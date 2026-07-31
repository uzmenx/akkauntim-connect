import * as THREE from 'three';
import {
    Fn, uniform, float, vec2, vec3, vec4,
    sin, cos, dot, cross, normalize, mix, pow, max, clamp, fract, smoothstep, distance, reflect,
    positionLocal, positionWorld, cameraPosition, pass
} from 'three/tsl';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';

async function init() {
    if (!navigator.gpu) {
        throw new Error("WebGPU is not supported by your browser.");
    }
    
    const renderer = new THREE.WebGPURenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    
    document.body.appendChild(renderer.domElement);
    
    await renderer.init();
    
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#05070a');
    
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.5, 8000);
    camera.position.set(0, 5.5, 17);
    
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.minDistance = 4;
    controls.maxDistance = 120;
    controls.minPolarAngle = 0.15;
    controls.maxPolarAngle = Math.PI * 0.495;
    controls.target.set(0, 1.5, 0);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.25;

    const uTime = uniform(0.0);
    const uSea = uniform(0.0);
    const uSunDir = uniform(vec3(0, 1, 0));
    const uSunColor = uniform(vec3(1, 1, 1));
    const uHorizonColor = uniform(vec3(0, 0, 0));
    const uZenithColor = uniform(vec3(0, 0, 0));
    const uDeepColor = uniform(vec3(0, 0, 0));
    const uShallowColor = uniform(vec3(0, 0, 0));

    const waves = [
        { dir: new THREE.Vector2(1.0, 0.0).normalize(), wl: 60.0, st: 0.12 },
        { dir: new THREE.Vector2(0.6, 0.8).normalize(), wl: 31.0, st: 0.12 },
        { dir: new THREE.Vector2(-0.7, 0.7).normalize(), wl: 18.0, st: 0.09 },
        { dir: new THREE.Vector2(0.3, -0.95).normalize(), wl: 9.5, st: 0.07 },
        { dir: new THREE.Vector2(-0.35, -0.94).normalize(), wl: 5.0, st: 0.05 }
    ].map(w => {
        const k = (2 * Math.PI) / w.wl;
        const c = Math.sqrt(9.8 * k);
        return { dir: w.dir, k, c, st: w.st };
    });

    const hash2 = Fn(([p_immutable]) => {
        const p = vec2(p_immutable).toVar();
        const d1 = dot(p, vec2(127.1, 311.7));
        const d2 = dot(p, vec2(269.5, 183.3));
        return fract(sin(vec2(d1, d2)).mul(43758.5453)).mul(2.0).sub(1.0);
    });

    const gradNoise = Fn(([p_immutable]) => {
        const p = vec2(p_immutable).toVar();
        const i = p.floor();
        const f = p.fract();
        
        const u = f.mul(f).mul(f).mul(f.mul(f.mul(6.0).sub(15.0)).add(10.0));
        
        const ga = hash2(i.add(vec2(0.0, 0.0)));
        const gb = hash2(i.add(vec2(1.0, 0.0)));
        const gc = hash2(i.add(vec2(0.0, 1.0)));
        const gd = hash2(i.add(vec2(1.0, 1.0)));
        
        const va = dot(ga, f.sub(vec2(0.0, 0.0)));
        const vb = dot(gb, f.sub(vec2(1.0, 0.0)));
        const vc = dot(gc, f.sub(vec2(0.0, 1.0)));
        const vd = dot(gd, f.sub(vec2(1.0, 1.0)));
        
        return mix(mix(va, vb, u.x), mix(vc, vd, u.x), u.y);
    });

    const fbm = Fn(([p_immutable]) => {
        const p = vec2(p_immutable).toVar();
        let value = gradNoise(p);
        value = value.add(gradNoise(p.mul(2.04).add(vec2(17.3, 9.1))).mul(0.5));
        value = value.add(gradNoise(p.mul(4.11).add(vec2(42.7, 28.6))).mul(0.25));
        return value;
    });

    const wavePosition = Fn(([xz_immutable, time_immutable, sea_immutable]) => {
        const xz = vec2(xz_immutable).toVar();
        const time = float(time_immutable).toVar();
        const sea = float(sea_immutable).toVar();
        const pos = vec3(xz.x, 0.0, xz.y).toVar();
        
        for (let i = 0; i < waves.length; i++) {
            const w = waves[i];
            const a = sea.mul(w.st).div(w.k);
            const phase = float(w.k).mul(dot(vec2(w.dir.x, w.dir.y), xz).sub(time.mul(w.c)));
            pos.x.addAssign(a.mul(w.dir.x).mul(cos(phase)));
            pos.y.addAssign(a.mul(sin(phase)));
            pos.z.addAssign(a.mul(w.dir.y).mul(cos(phase)));
        }
        return pos;
    });

    const waveNormal = Fn(([xz_immutable, time_immutable, sea_immutable]) => {
        const xz = vec2(xz_immutable).toVar();
        const time = float(time_immutable).toVar();
        const sea = float(sea_immutable).toVar();
        
        const tangent = vec3(1.0, 0.0, 0.0).toVar();
        const binormal = vec3(0.0, 0.0, 1.0).toVar();
        
        for (let i = 0; i < waves.length; i++) {
            const w = waves[i];
            const a = sea.mul(w.st).div(w.k);
            const phase = float(w.k).mul(dot(vec2(w.dir.x, w.dir.y), xz).sub(time.mul(w.c)));
            
            const wa = a.mul(w.k);
            const S = sin(phase);
            const C = cos(phase);
            
            tangent.x.subAssign(w.dir.x.mul(w.dir.x).mul(wa).mul(S));
            tangent.y.addAssign(w.dir.x.mul(wa).mul(C));
            tangent.z.subAssign(w.dir.x.mul(w.dir.y).mul(wa).mul(S));
            
            binormal.x.subAssign(w.dir.x.mul(w.dir.y).mul(wa).mul(S));
            binormal.y.addAssign(w.dir.y.mul(wa).mul(C));
            binormal.z.subAssign(w.dir.y.mul(w.dir.y).mul(wa).mul(S));
        }
        return normalize(cross(binormal, tangent));
    });

    const waveCrest = Fn(([xz_immutable, time_immutable, sea_immutable]) => {
        const xz = vec2(xz_immutable).toVar();
        const time = float(time_immutable).toVar();
        const sea = float(sea_immutable).toVar();
        const crest = float(0.0).toVar();
        
        for (let i = 0; i < waves.length; i++) {
            const w = waves[i];
            const a = sea.mul(w.st).div(w.k);
            const phase = float(w.k).mul(dot(vec2(w.dir.x, w.dir.y), xz).sub(time.mul(w.c)));
            crest.addAssign(a.mul(sin(phase)));
        }
        return crest;
    });

    const detailHeight = Fn(([xz_immutable, time_immutable]) => {
        const xz = vec2(xz_immutable).toVar();
        const time = float(time_immutable).toVar();
        const driftA = vec2(time.mul(0.55), time.mul(0.32));
        const driftB = vec2(time.mul(-0.4), time.mul(0.5));
        return fbm(xz.mul(0.85).add(driftA)).add(fbm(xz.mul(2.1).add(driftB)).mul(0.45));
    });

    const skyColor = Fn(([dir_immutable]) => {
        const dir = normalize(vec3(dir_immutable)).toVar();
        const up = clamp(dir.y, -0.15, 1.0);
        
        let color = mix(uHorizonColor, uZenithColor, pow(max(up, 0.0), 0.42));
        color = mix(color, uDeepColor.mul(1.4).add(uHorizonColor.mul(0.25)), smoothstep(0.0, -0.15, dir.y));
        
        const s = max(dot(dir, uSunDir), 0.0);
        color = color.add(uSunColor.mul(pow(s, 10.0)).mul(0.18));
        color = color.add(uSunColor.mul(smoothstep(0.9994, 0.9998, s)).mul(30.0));
        
        return color;
    });

    const skyMaterial = new THREE.MeshBasicNodeMaterial();
    skyMaterial.colorNode = Fn(() => {
        const dir = normalize(positionWorld.sub(cameraPosition));
        let color = skyColor(dir);
        
        const band = smoothstep(0.03, 0.16, dir.y).mul(smoothstep(0.6, 0.22, dir.y));
        const proj = dir.xz.div(dir.y.add(0.18)).mul(0.55);
        const drift = vec2(uTime.mul(0.006), uTime.mul(0.003));
        const cloudNoise = fbm(proj.add(drift)).mul(0.5).add(0.5);
        const cloudMask = smoothstep(0.62, 0.95, cloudNoise).mul(band);
        const warmCloud = vec3(0.92, 0.90, 0.87).mul(uSunColor).mul(1.2);
        
        color = mix(color, warmCloud, cloudMask.mul(0.6));
        
        return vec4(color, 1.0);
    })();
    skyMaterial.side = THREE.BackSide;
    skyMaterial.depthWrite = false;

    const skyGeo = new THREE.SphereGeometry(4000, 48, 24);
    const skyMesh = new THREE.Mesh(skyGeo, skyMaterial);
    skyMesh.renderOrder = -1;
    skyMesh.frustumCulled = false;
    scene.add(skyMesh);

    const oceanMaterial = new THREE.MeshBasicNodeMaterial();
    oceanMaterial.positionNode = wavePosition(positionLocal.xz, uTime, uSea);
    oceanMaterial.colorNode = Fn(() => {
        const P = positionWorld;
        const xz = P.xz;
        
        const N0 = waveNormal(xz, uTime, uSea);
        
        const h0 = detailHeight(xz, uTime);
        const hx = detailHeight(xz.add(vec2(0.1, 0.0)), uTime);
        const hz = detailHeight(xz.add(vec2(0.0, 0.1)), uTime);
        
        const dN = vec3(h0.sub(hx), 0.0, h0.sub(hz)).mul(float(1.5).mul(uSea.mul(0.6).add(0.4)));
        const N = normalize(N0.add(dN));
        
        const V = normalize(cameraPosition.sub(P));
        const crest = waveCrest(xz, uTime, uSea);
        
        const bodyColor = mix(uDeepColor, uShallowColor, clamp(crest.mul(0.35).add(0.45), 0.0, 1.0));
        
        let reflDir = reflect(V.negate(), N);
        reflDir.y = max(reflDir.y, 0.04);
        reflDir = normalize(reflDir);
        
        const skyRefl = skyColor(reflDir);
        
        const NdotV = max(dot(N, V), 0.0);
        const fresnel = float(0.02).add(float(0.98).mul(pow(float(1.0).sub(NdotV), 5.0)));
        
        // SSS tint before fresnel mix
        const VdotSun = max(dot(V, uSunDir), 0.0);
        const sss = pow(VdotSun, 3.0).mul(max(crest, 0.0)).mul(0.18);
        const sssColor = uShallowColor.mul(uSunColor).mul(sss);
        
        let color = mix(bodyColor.add(sssColor), skyRefl, fresnel);
        
        const H = normalize(uSunDir.add(V));
        const NdotH = max(dot(N, H), 0.0);
        
        const glitterLobe = pow(NdotH, 500.0);
        const glitterNoise = fbm(xz.mul(3.0).add(uTime)).mul(0.5).add(0.5);
        const glitter = glitterLobe.mul(glitterNoise).mul(2.0);
        
        const sheen = pow(NdotH, 48.0).mul(0.12);
        
        color = color.add(uSunColor.mul(glitter.add(sheen)));
        
        const foamNoise = fbm(xz.mul(1.1).add(vec2(uTime.mul(0.22), uTime.mul(0.14)))).mul(0.5).add(0.5);
        const foamMask = smoothstep(0.5, 0.95, foamNoise).mul(smoothstep(1.0, 2.0, crest));
        const foamColor = vec3(0.82, 0.88, 0.90);
        color = mix(color, foamColor, clamp(foamMask, 0.0, 0.85));
        
        const dist = distance(P, cameraPosition);
        color = mix(color, uHorizonColor, smoothstep(150.0, 290.0, dist));
        
        return vec4(color, 1.0);
    })();
    
    const oceanGeo = new THREE.PlaneGeometry(420, 420, 440, 440);
    oceanGeo.rotateX(-Math.PI / 2);
    const oceanMesh = new THREE.Mesh(oceanGeo, oceanMaterial);
    oceanMesh.frustumCulled = false;
    scene.add(oceanMesh);

    const postProcessing = new THREE.PostProcessing(renderer);
    const scenePass = pass(scene, camera);
    const sceneColor = scenePass.getTextureNode();
    postProcessing.outputNode = sceneColor.add(bloom(sceneColor, 0.4, 0.3, 0.9));

    const DAY = {
        zenith: new THREE.Color(0.07, 0.20, 0.42),
        horizon: new THREE.Color(0.52, 0.68, 0.82),
        sunBase: new THREE.Color(1.0, 0.93, 0.80),
        sunInt: 1.6,
        deep: new THREE.Color(0.015, 0.09, 0.11),
        shallow: new THREE.Color(0.06, 0.32, 0.36)
    };
    
    const DUSK = {
        zenith: new THREE.Color(0.03, 0.05, 0.16),
        horizon: new THREE.Color(0.85, 0.36, 0.16),
        sunBase: new THREE.Color(1.0, 0.42, 0.14),
        sunInt: 2.6,
        deep: new THREE.Color(0.02, 0.045, 0.075),
        shallow: new THREE.Color(0.09, 0.15, 0.20)
    };

    const inpSea = document.getElementById('inp-sea');
    const valSea = document.getElementById('val-sea');
    const inpTime = document.getElementById('inp-time');
    const valTime = document.getElementById('val-time');
    const btnDrift = document.getElementById('btn-drift');
    const valFps = document.getElementById('val-fps');
    
    function cubicSmoothstep(edge0, edge1, x) {
        const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
        return t * t * (3 - 2 * t);
    }

    function updateTimeOfDay() {
        const t = parseFloat(inpTime.value) / 100;
        
        const elevation = -0.05 + t * (0.62 - (-0.05));
        const azimuth = -0.9 + t * (0.9 - (-0.9));
        
        const sunDir = new THREE.Vector3(
            Math.cos(elevation) * Math.sin(azimuth),
            Math.sin(elevation),
            -Math.cos(elevation) * Math.cos(azimuth)
        ).normalize();
        
        uSunDir.value.copy(sunDir);
        
        const weight = cubicSmoothstep(0.0, 0.42, elevation);
        
        uZenithColor.value.copy(DUSK.zenith).lerp(DAY.zenith, weight);
        uHorizonColor.value.copy(DUSK.horizon).lerp(DAY.horizon, weight);
        uDeepColor.value.copy(DUSK.deep).lerp(DAY.deep, weight);
        uShallowColor.value.copy(DUSK.shallow).lerp(DAY.shallow, weight);
        
        const sunBase = DUSK.sunBase.clone().lerp(DAY.sunBase, weight);
        const sunInt = DUSK.sunInt + weight * (DAY.sunInt - DUSK.sunInt);
        uSunColor.value.copy(sunBase).multiplyScalar(sunInt);
        
        let label = "MIDDAY";
        if (t < 0.12) label = "DUSK";
        else if (t < 0.30) label = "GOLDEN HOUR";
        else if (t < 0.62) label = "AFTERNOON";
        valTime.textContent = label;
    }

    function updateSeaState() {
        const val = parseFloat(inpSea.value);
        valSea.textContent = val.toString();
        uSea.value = 0.25 + (val / 100) * 1.5;
    }

    inpTime.addEventListener('input', updateTimeOfDay);
    inpSea.addEventListener('input', updateSeaState);
    
    btnDrift.addEventListener('click', () => {
        controls.autoRotate = !controls.autoRotate;
        if (controls.autoRotate) {
            btnDrift.classList.add('active');
        } else {
            btnDrift.classList.remove('active');
        }
    });

    updateTimeOfDay();
    updateSeaState();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    let lastTime = performance.now();
    let frameCount = 0;
    let lastFpsTime = lastTime;
    let firstFrameRendered = false;

    function render(currentTime) {
        const dtRaw = (currentTime - lastTime) / 1000;
        lastTime = currentTime;
        const dt = Math.min(dtRaw, 0.1);
        
        uTime.value += dt;
        controls.update();
        
        postProcessing.render();
        
        frameCount++;
        if (currentTime - lastFpsTime >= 500) {
            const fps = Math.round((frameCount * 1000) / (currentTime - lastFpsTime));
            valFps.textContent = fps + " FPS";
            frameCount = 0;
            lastFpsTime = currentTime;
        }

        if (!firstFrameRendered) {
            firstFrameRendered = true;
            document.getElementById('loader').style.opacity = '0';
            setTimeout(() => {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('ui').classList.add('visible');
            }, 900);
        }
    }

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            renderer.setAnimationLoop(null);
        } else {
            lastTime = performance.now();
            renderer.setAnimationLoop(render);
        }
    });

    renderer.setAnimationLoop(render);
}

init().catch(err => {
    console.error(err);
    document.getElementById('loader').style.display = 'none';
    const errDiv = document.getElementById('error');
    errDiv.style.display = 'flex';
    document.getElementById('error-msg').textContent = err.message || "Initialization failed.";
});
