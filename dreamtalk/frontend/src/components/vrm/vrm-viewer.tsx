'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

export interface VrmViewerProps {
  modelUrl: string | null;
  className?: string;
  style?: React.CSSProperties;
  centered?: boolean;
  locked?: boolean;
  overlay?: boolean;
  onLoad?: (vrm: any) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: number) => void;
  cameraDistance?: number;
  children?: React.ReactNode;
}

export interface VrmViewerHandle {
  setExpression: (name: string, value: number) => void;
  updateExpression: (delta: number) => void;
  getVRM: () => any | null;
}

function isObjUrl(url: string): boolean {
  return url.toLowerCase().endsWith('.obj');
}

function VRMScene({
  modelUrl,
  onLoad,
  onError,
  onProgress,
  centered,
  locked,
  overlay,
  cameraDistance,
}: {
  modelUrl: string | null;
  onLoad?: (vrm: any) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: number) => void;
  centered?: boolean;
  locked?: boolean;
  overlay?: boolean;
  cameraDistance?: number;
}) {
  const { camera, scene } = useThree();
  const vrmRef = useRef<any>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const [vrmLoaded, setVrmLoaded] = useState(false);

  useEffect(() => {
    if (!modelUrl) return;

    let mounted = true;
    let currentGroup: THREE.Group | null = null;

    // ── OBJ Loader (FLAME meshes, generic OBJ files) ──
    async function loadOBJ() {
      try {
        const [{ OBJLoader }, { MTLLoader }] = await Promise.all([
          import('three/examples/jsm/loaders/OBJLoader.js'),
          import('three/examples/jsm/loaders/MTLLoader.js'),
        ]);

        const objLoader = new OBJLoader();
        const mtlUrl = modelUrl!.replace(/\.obj$/i, '.mtl');

        // Try loading MTL first
        try {
          const mtlLoader = new MTLLoader();
          const materials = await mtlLoader.loadAsync(mtlUrl);
          materials.preload();
          objLoader.setMaterials(materials);
        } catch {
          console.log('MTL not found, using default material');
        }

        objLoader.load(
          modelUrl!,
          (obj) => {
            if (!mounted) return;
            currentGroup = obj as unknown as THREE.Group;

            // Center and scale the model
            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const scale = maxDim > 0 ? 1.5 / maxDim : 1;
            obj.scale.set(scale, scale, scale);
            obj.position.set(
              -center.x * scale,
              -center.y * scale + size.y * scale * 0.3,
              -center.z * scale
            );

            obj.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                if (!child.material || (child.material as any).constructor?.name === 'Material') {
                  child.material = new THREE.MeshPhysicalMaterial({
                    color: '#e8c4a0',
                    metalness: 0.02,
                    roughness: 0.6,
                    clearcoat: 0.05,
                  });
                }
              }
            });

            scene.add(currentGroup!);
            vrmRef.current = { scene: currentGroup };
            setVrmLoaded(true);
            onLoad?.({ scene: currentGroup, isOBJ: true });
          },
          (xhr) => {
            if (xhr.total && onProgress) {
              onProgress(Math.round((xhr.loaded / xhr.total) * 100));
            }
          },
          (error) => {
            console.error('OBJ load error:', error);
            onError?.('Failed to load 3D model');
          }
        );
      } catch (err) {
        if (!mounted) return;
        console.warn('OBJ loader import failed:', err);
        onError?.('3D model loader not available');
      }
    }

    // ── VRM Loader (VRM/VRMA files) ──
    async function loadVRM() {
      try {
        const { GLTFLoader } = await import(
          'three/examples/jsm/loaders/GLTFLoader.js'
        );
        const { VRMLoaderPlugin, VRMUtils } = await import(
          '@pixiv/three-vrm'
        );

        const loader = new GLTFLoader();
        loader.crossOrigin = 'anonymous';
        loader.register((parser: any) => new VRMLoaderPlugin(parser));

        loader.load(
          modelUrl!,
          (gltf: any) => {
            if (!mounted) return;
            const loadedVrm = gltf.userData.vrm;

            VRMUtils.removeUnnecessaryVertices(loadedVrm.scene);
            VRMUtils.removeUnnecessaryJoints(loadedVrm.scene);

            loadedVrm.scene.traverse((obj: THREE.Object3D) => {
              obj.frustumCulled = false;
              if (obj instanceof THREE.Mesh) {
                obj.castShadow = true;
                obj.receiveShadow = true;
              }
            });

            const box = new THREE.Box3().setFromObject(loadedVrm.scene);
            const center = box.getCenter(new THREE.Vector3());
            loadedVrm.scene.position.x = -center.x;
            loadedVrm.scene.position.z = -center.z;
            loadedVrm.scene.position.y = -box.min.y;

            const humanoid = loadedVrm.humanoid;
            if (humanoid) {
              const leftUpperArm =
                humanoid.getNormalizedBoneNode('leftUpperArm');
              const rightUpperArm =
                humanoid.getNormalizedBoneNode('rightUpperArm');
              if (leftUpperArm)
                leftUpperArm.rotation.set(0.05, 0, -0.4);
              if (rightUpperArm)
                rightUpperArm.rotation.set(0.05, 0, 0.4);
            }

            scene.add(loadedVrm.scene);
            vrmRef.current = loadedVrm;
            mixerRef.current = new THREE.AnimationMixer(loadedVrm.scene);
            setVrmLoaded(true);
            onLoad?.(loadedVrm);
          },
          (xhr: any) => {
            if (xhr.total && onProgress) {
              onProgress(Math.round((xhr.loaded / xhr.total) * 100));
            }
          },
          (error: any) => {
            console.error('VRM load error:', error);
            // VRM failed — try OBJ as fallback
            if (mounted && modelUrl) {
              console.log('VRM failed, trying OBJ fallback...');
              loadOBJ();
            } else {
              onError?.('Failed to load 3D model');
            }
          }
        );
      } catch (err) {
        if (!mounted) return;
        console.warn('VRM import failed, trying OBJ:', err);
        loadOBJ();
      }
    }

    // Route to correct loader based on file extension
    if (isObjUrl(modelUrl)) {
      loadOBJ();
    } else {
      loadVRM();
    }

    return () => {
      mounted = false;
      if (vrmRef.current) {
        scene.remove(vrmRef.current.scene);
        vrmRef.current = null;
      }
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current = null;
      }
    };
  }, [modelUrl]);

  useFrame((_, delta) => {
    mixerRef.current?.update(delta);
    vrmRef.current?.update(delta);
  });

  useEffect(() => {
    if (camera && cameraDistance) {
      camera.position.set(0, 1.15, cameraDistance);
    }
  }, [camera, cameraDistance]);

  return null;
}

function VrmViewerComponent({
  modelUrl,
  className,
  style,
  centered = false,
  locked = false,
  overlay = false,
  onLoad,
  onError,
  onProgress,
  cameraDistance = 3.5,
  children,
}: VrmViewerProps, ref: React.Ref<VrmViewerHandle>) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  React.useImperativeHandle(ref, () => ({
    setExpression: (_name: string, _value: number) => {},
    updateExpression: (_delta: number) => {},
    getVRM: () => null,
  }));

  if (!isMounted) {
    return (
      <div
        className={`flex items-center justify-center bg-neutral-100 dark:bg-neutral-800 ${className || ''}`}
        style={style}
      >
        <div className='text-neutral-400'>Initializing 3D viewer...</div>
      </div>
    );
  }

  return (
    <div
      className={`relative ${overlay ? '' : 'overflow-hidden'} ${className || ''}`}
      style={style}
    >
      <Canvas
        camera={{
          position: [0, 1.15, cameraDistance],
          fov: 30,
          near: 0.1,
          far: 20,
        }}
        gl={{
          antialias: true,
          alpha: true,
          preserveDrawingBuffer: true,
        }}
        style={{ width: '100%', height: '100%' }}
      >
        {!overlay && (
          <>
            <color attach='background' args={['#ffffff']} />
            <ambientLight intensity={0.5} />
            <hemisphereLight
              args={[0x87ceeb, 0xffe4b5, 2]}
              position={[0, 50, 0]}
            />
            <directionalLight
              position={[-30, 52.5, 30]}
              intensity={3}
              castShadow
              shadow-mapSize-width={2048}
              shadow-mapSize-height={2048}
              shadow-camera-left={-3}
              shadow-camera-right={3}
              shadow-camera-top={3}
              shadow-camera-bottom={-3}
              shadow-camera-far={100}
              shadow-bias={-0.0001}
            />
            <mesh rotation-x={-Math.PI / 2} position-y={0} receiveShadow>
              <circleGeometry args={[2, 64]} />
              <shadowMaterial opacity={0.15} />
            </mesh>
          </>
        )}
        {!locked && <OrbitControls enableDamping minDistance={0.5} maxDistance={5} />}
        <VRMScene
          modelUrl={modelUrl}
          onLoad={onLoad}
          onError={onError}
          onProgress={onProgress}
          centered={centered}
          locked={locked}
          overlay={overlay}
          cameraDistance={cameraDistance}
        />
        {children}
      </Canvas>
    </div>
  );
}

export const VrmViewer = React.forwardRef(VrmViewerComponent);
export default VrmViewer;
