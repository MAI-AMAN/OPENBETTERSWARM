# OpenBetterSwarm - Planner Progress Bubble

OpenBetterSwarm is an enhanced AI agent orchestration platform that introduces deep visibility into the agent's thought process before it takes action. 

## The Planner Progress Bubble Feature

When interacting with complex AI agents, the initial planning stage can sometimes appear as "dead time" where the user is left wondering if the system is working. The **Planner Progress Bubble** eliminates this uncertainty by bringing backend orchestrator thoughts directly into the frontend chat interface in real-time.

### Key Capabilities

- **Real-Time Transparency**: Leveraging a robust WebSocket connection, the backend broadcasts `agent:planner_status` events continuously. Users see exactly what the agent is doing at any given millisecond.
- **Granular Status Tracking**: The UI tracks every step of the agent's pre-execution flow, including:
  - Task Classification
  - Workflow Selection
  - Metric Analysis
  - Execution Plan Generation
- **Seamless UI/UX**: Built with React and Framer Motion, the progress bubble animates smoothly into the chat view. It features a glowing, glassmorphic design that perfectly matches modern AI chat interfaces, providing a premium feel.
- **Zero-Leak State Management**: The planner's state is strictly managed using Redux Toolkit. Once the planning phase completes, the bubble seamlessly transitions out, ensuring a clean chat history with no lingering loading artifacts.

### How it Works Under the Hood

1. **Backend Orchestrator**: The backend (Python/FastAPI) executes the planning phases. As it progresses, it emits structured WebSocket messages tagged as `agent:planner_status` with `step` and `message` payloads.
2. **WebSocket Manager**: The React frontend intercepts these messages and dispatches them to the global Redux store (`streamingSlice.ts`).
3. **Dynamic Rendering**: The `PlannerProgressBubble.tsx` component listens to this state and visually renders the current step alongside a pulsing circular progress indicator.

---

## How to Run the Application

Follow these steps to launch the entire OpenBetterSwarm stack locally on your machine:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MAI-AMAN/OPENBETTERSWARM.git
   cd OPENBETTERSWARM
   ```

2. **Run the initialization script**:
   ```bash
   bash run.sh
   ```

   *The `run.sh` script is a unified command that will automatically:*
   - Create a virtual environment and install backend dependencies (Python).
   - Install frontend dependencies (Node.js/npm).
   - Install Electron shell dependencies.
   - Start the FastAPI backend on port `8324`.
   - Start the React frontend on port `3000`.
   - Launch the Electron desktop application window.

> **Note**: Ensure you have Python 3.11+ and Node.js 18+ installed on your system before running the script.
