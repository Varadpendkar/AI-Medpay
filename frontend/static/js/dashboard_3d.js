// dashboard_3d.js - small Three.js accent (low poly rotating ring)
(function(){
  const script = document.createElement('script');
  script.src = 'https://unpkg.com/three@0.158.0/build/three.min.js';
  script.onload = init;
  document.head.appendChild(script);

  function init(){
    const el = document.getElementById('dashboard-3d');
    if (!el) return;
    
    // Check for reduced motion preference
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    
    const w = el.clientWidth, h = el.clientHeight;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, w/h, 0.1, 1000);
    camera.position.z = 3;

    // Lighting setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // Create the main torus (ring)
    const geom = new THREE.TorusGeometry(0.6, 0.15, 16, 64);
    const mat = new THREE.MeshStandardMaterial({ 
      color: 0x00a693, 
      metalness: 0.3, 
      roughness: 0.6,
      transparent: true,
      opacity: 0.9
    });
    const torus = new THREE.Mesh(geom, mat);
    scene.add(torus);

    // Add small orbiting elements
    const orbitGroup = new THREE.Group();
    scene.add(orbitGroup);
    
    for(let i = 0; i < 3; i++) {
      const smallGeom = new THREE.SphereGeometry(0.05, 8, 8);
      const smallMat = new THREE.MeshStandardMaterial({ 
        color: 0x0ea5e9,
        transparent: true,
        opacity: 0.7
      });
      const sphere = new THREE.Mesh(smallGeom, smallMat);
      
      const angle = (i / 3) * Math.PI * 2;
      sphere.position.x = Math.cos(angle) * 1.2;
      sphere.position.y = Math.sin(angle) * 1.2;
      
      orbitGroup.add(sphere);
    }

    let clock = new THREE.Clock();
    
    function animate(){
      const elapsed = clock.getElapsedTime();
      
      // Rotate main torus
      torus.rotation.x += 0.008;
      torus.rotation.y += 0.01;
      
      // Orbit small spheres
      orbitGroup.rotation.z = elapsed * 0.5;
      
      // Subtle floating motion
      torus.position.y = Math.sin(elapsed * 0.8) * 0.1;
      
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }
    animate();

    // Handle resize
    window.addEventListener('resize', () => {
      if (el.clientWidth && el.clientHeight) {
        renderer.setSize(el.clientWidth, el.clientHeight);
        camera.aspect = el.clientWidth / el.clientHeight;
        camera.updateProjectionMatrix();
      }
    });
  }
})();