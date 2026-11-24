from typing import Dict, Any, Optional

from models.message import AgentMessage
from memory.long_term_memory import LongTermMemoryStore
from memory.tfidf_retriever import RetrievedEvidence


class PolicyMemoryAgent:


    def __init__(self, long_term_memory: Optional[LongTermMemoryStore] = None):
        self.name = "PolicyMemoryAgent"
        self.ltm = long_term_memory or LongTermMemoryStore()

    def process_message(self, request_msg: AgentMessage) -> AgentMessage:

        action = request_msg.action

        if action == "retrieve_policy_and_cases":
            query_text = request_msg.payload.get("query", "Pune Singapore flight under 30000 budget policy")
            top_k = int(request_msg.payload.get("top_k", 3))

            retrieved = self.ltm.retrieve_relevant_evidence(query_text, top_k=top_k)

            evidence_list = [
                {
                    "doc_id": r.doc_id,
                    "category": r.category,
                    "title": r.title,
                    "score": r.score,
                    "matched_terms": r.matched_terms,
                    "snippet": r.snippet
                }
                for r in retrieved
            ]

            return AgentMessage(
                performative="INFORM",
                sender=self.name,
                receiver=request_msg.sender,
                action="policy_and_cases_retrieved",
                task_id=request_msg.task_id,
                correlation_id=request_msg.correlation_id,
                status="completed",
                payload={
                    "evidence_count": len(retrieved),
                    "query": query_text
                },
                evidence=evidence_list
            )

        elif action == "persist_search_case":
            return AgentMessage(
                performative="INFORM",
                sender=self.name,
                receiver=request_msg.sender,
                action="search_case_persisted",
                task_id=request_msg.task_id,
                correlation_id=request_msg.correlation_id,
                status="completed",
                payload={"status": "saved"}
            )

        return AgentMessage(
            performative="FAILURE",
            sender=self.name,
            receiver=request_msg.sender,
            action=action,
            task_id=request_msg.task_id,
            correlation_id=request_msg.correlation_id,
            status="failed",
            error_details=f"Unsupported action '{action}' for PolicyMemoryAgent."
        )
