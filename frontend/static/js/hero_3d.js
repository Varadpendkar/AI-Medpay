// hero_3d.js - Three.js floating card + particles
// requires three.js from CDN
(function() {
  // lazy-load Three.js from CDN
  const script = document.createElement('script');
  script.src = 'https://unpkg.com/three@0.158.0/build/three.min.js';
  script.onload = init;
  document.head.appendChild(script);

  function init() {
    const canvasWrapper = document.getElementById('hero-3d-canvas');
    if (!canvasWrapper) return;

    // Create renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(canvasWrapper.clientWidth, canvasWrapper.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    canvasWrapper.appendChild(renderer.domElement);

    // Scene + camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, canvasWrapper.clientWidth / canvasWrapper.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 6);

    // Light
    const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
    scene.add(hemi);

    // Floating "card" geometry
    const geometry = new THREE.BoxGeometry(3.2, 2, 0.08);
    const material = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6, metalness: 0.1 });
    const card = new THREE.Mesh(geometry, material);

    // simulate layered glossy surface
    const borderGeom = new THREE.EdgesGeometry(geometry);
    const border = new THREE.LineSegments(borderGeom, new THREE.LineBasicMaterial({ color: 0x00a693, linewidth: 1 }));
    card.add(border);

    scene.add(card);

    // Particles (small points)
    const particlesCount = 120;
    const positions = new Float32Array(particlesCount * 3);
    for (let i=0; i<particlesCount; i++) {
      positions[i*3 + 0] = (Math.random() - 0.5) * 8;
      positions[i*3 + 1] = (Math.random() - 0.5) * 4;
      positions[i*3 + 2] = (Math.random() - 0.5) * 4;
    }
    const particlesGeom = new THREE.BufferGeometry();
    particlesGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particlesMat = new THREE.PointsMaterial({ color: 0x86efac, size: 0.06, transparent: true, opacity: 0.9 });
    const particles = new THREE.Points(particlesGeom, particlesMat);
    scene.add(particles);

    // animation loop
    let clock = new THREE.Clock();
    function animate() {
      const t = clock.getElapsedTime();

      // slow rotation + float
      card.rotation.y = Math.sin(t * 0.3) * 0.12;
      card.rotation.x = Math.sin(t * 0.2) * 0.08;
      card.position.y = Math.sin(t * 0.6) * 0.12;

      // subtle particle drift
      const pos = particlesGeom.attributes.position.array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i+1] += Math.sin(t * 0.25 + i) * 0.0006;
      }
      particlesGeom.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }

    animate();

    // resize handling
    window.addEventListener('resize', () => {
      renderer.setSize(canvasWrapper.clientWidth, canvasWrapper.clientHeight);
      camera.aspect = canvasWrapper.clientWidth / canvasWrapper.clientHeight;
      camera.updateProjectionMatrix();
    });
  }
})();