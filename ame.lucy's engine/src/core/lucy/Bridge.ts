export const AmeBridge = {
  init: () => {
    window.addEventListener('message', (event) => {
      // Validate origin (Lucy OS runs on 3000)
      if (event.origin !== 'http://localhost:3000') return;

      const { command, payload } = event.data;
      
      switch(command) {
        case 'TOGGLE_RAYTRACING':
          console.log("Lucy requested Raytracing:", payload);
          // Trigger internal state change
          break;
        case 'LOAD_MESH':
          console.log("Lucy requested Mesh Load:", payload);
          break;
        case 'SPAWN_ENTITY':
          console.log("Lucy requested Entity Spawn:", payload);
          // e.g., payload = { id: 'NPC_1', type: 'Ped', coords: {x: 0, y: 0, z: 0} }
          break;
        case 'DYNAMIC_MISSION':
          console.log("Lucy pushed Dynamic Mission:", payload);
          // e.g., payload = { id: 'M_1', objective: 'Secure the area', zone: 'Downtown' }
          break;
        case 'QUERY_WORLD':
          console.log("Lucy queried World State:", payload);
          AmeBridge.sendToLucy('WORLD_STATE_RESPONSE', {
            zones: ['Downtown', 'Vinewood'],
            entities: ['TorusKnot_01', 'PointLight_01']
          });
          break;
        case 'INIT_SUCCESS':
          console.log("Lucy OS connection established.");
          break;
      }
    });
    
    // Notify Lucy OS we are ready
    if (window.parent !== window) {
        AmeBridge.sendToLucy('AME_READY', { status: 'online' });
    }
  },
  
  sendToLucy: (type: string, payload: any) => {
    window.parent.postMessage({
      type,
      payload
    }, 'http://localhost:3000');
  }
};
