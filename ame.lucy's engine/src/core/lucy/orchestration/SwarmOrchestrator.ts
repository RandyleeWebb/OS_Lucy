import { HardStateIsolation } from './HardStateIsolation';
import { eventBus } from '../EventBus';

export type SwarmAgent = {
  id: string;
  name: string;
  /**
   * Untrusted external logic. The agent proposes an action based on the state it sees.
   */
  proposeAction: (readOnlyState: any) => Promise<any>;
};

export class SwarmOrchestrator {
  private agents: Map<string, SwarmAgent> = new Map();

  registerAgent(agent: SwarmAgent) {
    this.agents.set(agent.id, agent);
    console.log(`[Swarm] Registered external agent: ${agent.name} (${agent.id})`);
  }

  /**
   * Safely executes an untrusted agent's logic using HardStateIsolation.
   */
  async delegateToAgent(agentId: string, actionSignature: string) {
    const agent = this.agents.get(agentId);
    if (!agent) {
      throw new Error(`Agent ${agentId} not found`);
    }

    eventBus.publish({
      type: 'SYSTEM_LOG',
      payload: { message: `[Swarm] Delegating task '${actionSignature}' to Agent '${agent.name}'...` }
    });

    // 🛡️ THE ISOLATION WRAPPER IN ACTION 🛡️
    // We pass the agent's untrusted `proposeAction` method into the HardStateIsolation wrapper.
    // The wrapper ensures the agent only receives a frozen clone of the state and enforces gravity.
    const result = await HardStateIsolation.execute(
      agent.id,
      actionSignature,
      async (readOnlyState) => {
        // The agent executes its logic here. If it tries to mutate `readOnlyState`, 
        // it will fail (because it's frozen). If it throws an error, the wrapper catches it.
        return await agent.proposeAction(readOnlyState);
      }
    );

    if (result.success) {
      eventBus.publish({
        type: 'SYSTEM_LOG',
        payload: { message: `[Swarm] Agent '${agent.name}' succeeded. Proposed Data: ${JSON.stringify(result.data)}` }
      });
      
      // At this point, the Swarm Orchestrator can take the `result.data` and safely 
      // apply it to the real WorldModel using trusted, internal methods.
      
    } else {
      eventBus.publish({
        type: 'SYSTEM_LOG',
        payload: { 
          message: `[Swarm] Agent '${agent.name}' blocked or failed. Reason: ${result.error}. Penalty applied: ${result.gravityPenaltyApplied || 0}` 
        }
      });
    }

    return result;
  }
}

export const swarmOrchestrator = new SwarmOrchestrator();
