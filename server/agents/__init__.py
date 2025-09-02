"""
Agents Package - Human-AI Co-Creation System
Contains all AI agents for content generation, analysis, and verification
"""

# Direct imports for basic functionality - avoid complex orchestrator for now
__all__ = [
    "SessionManager",
    "PerceptionAgent",
    "PlannerGeneratorAgent",
    "GraphManagerAgent",
    "VerifierAgent",
    "EvaluatorAgent",
]


# Agent creation factory functions
async def create_session_manager(
    config, database_client=None, graph_client=None, llm_provider=None
):
    """Create and initialize session manager"""
    return SessionManager(config, database_client, graph_client, llm_provider)


async def create_perception_agent(config, llm_provider=None):
    """Create and initialize perception agent"""
    return PerceptionAgent(config, llm_provider)


async def create_planner_agent(config, llm_provider=None):
    """Create and initialize planner agent"""
    return PlannerAgent(config, llm_provider)


async def create_graph_manager(config, graph_client=None):
    """Create and initialize graph manager"""
    return GraphManager(config, graph_client)


async def create_verifier_agent(config, llm_provider=None):
    """Create and initialize verifier agent"""
    return VerifierAgent(config, llm_provider)


# Agent orchestration
class AgentOrchestrator:
    """Orchestrates multiple agents for complete co-creation workflow"""

    def __init__(
        self, config, database_client=None, graph_client=None, llm_provider=None
    ):
        self.config = config
        self.database_client = database_client
        self.graph_client = graph_client
        self.llm_provider = llm_provider

        # Agents will be initialized lazily
        self._session_manager = None
        self._perception_agent = None
        self._planner_agent = None
        self._graph_manager = None
        self._verifier_agent = None

    async def get_session_manager(self):
        """Get or create session manager"""
        if self._session_manager is None:
            self._session_manager = await create_session_manager(
                self.config, self.database_client, self.graph_client, self.llm_provider
            )
        return self._session_manager

    async def get_perception_agent(self):
        """Get or create perception agent"""
        if self._perception_agent is None:
            self._perception_agent = await create_perception_agent(
                self.config, self.llm_provider
            )
        return self._perception_agent

    async def get_planner_agent(self):
        """Get or create planner agent"""
        if self._planner_agent is None:
            self._planner_agent = await create_planner_agent(
                self.config, self.llm_provider
            )
        return self._planner_agent

    async def get_graph_manager(self):
        """Get or create graph manager"""
        if self._graph_manager is None:
            self._graph_manager = await create_graph_manager(
                self.config, self.graph_client
            )
        return self._graph_manager

    async def get_verifier_agent(self):
        """Get or create verifier agent"""
        if self._verifier_agent is None:
            self._verifier_agent = await create_verifier_agent(
                self.config, self.llm_provider
            )
        return self._verifier_agent

    async def run_complete_workflow(self, session_id: str, user_input: str = ""):
        """Run complete co-creation workflow"""
        session_manager = await self.get_session_manager()
        perception_agent = await self.get_perception_agent()
        planner_agent = await self.get_planner_agent()
        graph_manager = await self.get_graph_manager()
        verifier_agent = await self.get_verifier_agent()

        # 1. Load or create session
        workspace = await session_manager.load_workspace(session_id)
        if not workspace:
            return {"error": "Session not found"}

        # 2. Update workspace with user input if provided
        if user_input.strip():
            workspace = await session_manager.update_workspace(workspace, user_input)

        # 3. Analyze current state
        analysis = await perception_agent.invoke(workspace, {})

        # 4. Generate projections
        projections = await planner_agent.invoke(workspace, {})

        # 5. Verify projections
        verification_results = await verifier_agent.invoke(workspace, projections, {})

        # 6. Update knowledge graph
        await graph_manager.update_graph(workspace, projections)

        # 7. Save updated workspace
        await session_manager.save_workspace(workspace)

        return {
            "session_id": session_id,
            "workspace": workspace.dict(),
            "analysis": analysis,
            "projections": {k: v.dict() for k, v in projections.items()},
            "verification": {k: v.dict() for k, v in verification_results.items()},
        }


__all__ = [
    "SessionManager",
    "PromptTemplateGenerator",
    "PerceptionAgent",
    "PlannerAgent",
    "GraphManager",
    "VerifierAgent",
    "AgentOrchestrator",
    "create_session_manager",
    "create_perception_agent",
    "create_planner_agent",
    "create_graph_manager",
    "create_verifier_agent",
]
