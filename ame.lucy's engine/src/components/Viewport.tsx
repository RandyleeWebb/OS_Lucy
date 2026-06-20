import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

interface ViewportProps {
  activeLayer: 'geometry' | 'albedo' | 'normal' | 'wireframe' | 'lighting';
  onStatsUpdate: (stats: { fps: number; drawCalls: number; triangles: number }) => void;
  rayTracingEnabled: boolean;
}

export const Viewport: React.FC<ViewportProps> = ({ activeLayer, onStatsUpdate, rayTracingEnabled }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const frameIdRef = useRef<number>(0);
  const clockRef = useRef(new THREE.Clock());

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    sceneRef.current = scene;

    // Camera Setup
    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(5, 5, 5);
    cameraRef.current = camera;

    // Renderer Setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(10, 10, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);

    // RT Specific Light for GI simulation
    const rtLight = new THREE.PointLight(0x3b82f6, 0, 20);
    rtLight.position.set(-5, 2, -5);
    scene.add(rtLight);

    // Grid Helper
    const grid = new THREE.GridHelper(20, 20, 0x262626, 0x1a1a1a);
    scene.add(grid);

    // 8K World Simulation Objects
    const group = new THREE.Group();
    scene.add(group);

    // Create a complex "8K" style mesh
    const geometry = new THREE.TorusKnotGeometry(1.5, 0.5, 200, 32);
    const material = new THREE.MeshStandardMaterial({
      color: 0x3b82f6,
      roughness: 0.1,
      metalness: 0.8,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);

    // Add some "floating" data points
    for (let i = 0; i < 50; i++) {
      const dotGeo = new THREE.SphereGeometry(0.05);
      const dotMat = new THREE.MeshBasicMaterial({ color: 0x60a5fa });
      const dot = new THREE.Mesh(dotGeo, dotMat);
      dot.position.set(
        (Math.random() - 0.5) * 10,
        Math.random() * 5,
        (Math.random() - 0.5) * 10
      );
      group.add(dot);
    }

    // Materials for different layers
    const materials = {
      default: material,
      normal: new THREE.MeshNormalMaterial(),
      geometry: new THREE.MeshStandardMaterial({ color: 0x888888 }),
    };

    // Animation Loop
    let lastTime = performance.now();
    let frames = 0;

    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      
      const time = performance.now();
      frames++;
      
      if (time > lastTime + 1000) {
        onStatsUpdate({
          fps: Math.round((frames * 1000) / (time - lastTime)),
          drawCalls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles
        });
        lastTime = time;
        frames = 0;
      }

      // Layer Logic
      if (activeLayer === 'normal') {
        (mesh.material as THREE.Material) = materials.normal;
      } else if (activeLayer === 'geometry') {
        (mesh.material as THREE.Material) = materials.geometry;
      } else {
        (mesh.material as THREE.Material) = materials.default;
      }

      // Handle wireframe
      if ('wireframe' in mesh.material) {
        (mesh.material as any).wireframe = activeLayer === 'wireframe';
      }

      // Ray Tracing Simulation Logic
      if (rayTracingEnabled) {
        material.metalness = 0.95;
        material.roughness = 0.05;
        rtLight.intensity = 2.5;
        rtLight.position.x = Math.sin(time * 0.001) * 5;
        rtLight.position.z = Math.cos(time * 0.001) * 5;
        
        // Simulate higher load
        if (Math.random() > 0.9) frames -= 1; 
      } else {
        material.metalness = 0.8;
        material.roughness = 0.1;
        rtLight.intensity = 0;
      }

      mesh.rotation.y += 0.005;
      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(frameIdRef.current);
      renderer.dispose();
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement);
      }
    };
  }, [activeLayer, rayTracingEnabled]);

  return (
    <div ref={containerRef} className="w-full h-full relative bg-editor-bg">
      <div className="absolute top-4 left-4 pointer-events-none">
        <div className="bg-black/60 backdrop-blur-md border border-editor-border p-3 rounded-lg flex flex-col gap-1">
          <div className="text-[10px] uppercase tracking-widest text-editor-text-muted font-bold">AME Runtime v0.1.0-alpha</div>
          <div className="text-xs font-mono text-editor-accent">8K VIRTUALIZED PIPELINE ACTIVE</div>
          {rayTracingEnabled && (
            <div className="flex items-center gap-2 mt-1">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
              <div className="text-[9px] font-bold text-amber-500 uppercase tracking-tighter">Vulkan Ray Tracing Enabled</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
