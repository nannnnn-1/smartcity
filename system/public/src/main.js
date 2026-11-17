import * as THREE from 'three';
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { createScene, flyCamera } from './scene.js';
import { buildTerrain, buildBuildings, buildVectors, buildTrees, buildLabels } from './city.js';
import { createWater } from './water.js';
import { createRain } from './rain.js';
import { createSensors } from './markers.js';
import { ui } from './ui.js';
import { b64ToU8, clamp } from './utils.js';

const app = {
  meta: null, sensors: [], scenario: null, idx: 0, playing: false, speed: 1,
  currentDepth: null, layers: { water: true, buildings: true, roads: true, sensors: true, rain: true, labels: true },
  selectedId: null,
};

const loaderBar = document.getElementById('loader-bar');
const loaderStep = document.getElementById('loader-step');
function progress(p, text) {
  loaderBar.style.width = `${p}%`;
  if (text) loaderStep.textContent = text;
}

const fetchJSON = (u) => fetch(u, { cache: 'no-cache' }).then((r) => {
  if (!r.ok) throw new Error(`${u} ${r.status}`);
  return r.json();
});

async function boot() {
  try {
    progress(6, '加载空间元数据…');
    const meta = await fetchJSON('./data/meta.json');
    app.meta = meta;

    progress(12, '加载 5m 数字高程模型与地表覆盖…');
    const terrainData = await fetchJSON('./data/terrain.json');
    progress(28, '加载 3,800+ 建筑体块与路网…');
    const [buildings, vectors, sensors, scenarios] = await Promise.all([
      fetchJSON('./data/buildings.json'),
      fetchJSON('./data/vectors.json'),
      fetchJSON('./data/sensors.json'),
      fetchJSON('./data/scenarios/index.json'),
    ]);
    app.sensors = sensors;
    app.scenarios = scenarios;

    progress(42, '初始化三维渲染引擎…');
    const { renderer, scene, camera, controls, composer } = createScene(document.getElementById('scene-wrap'));
    window.__camera = camera;
    app.renderer = renderer; app.scene = scene; app.camera = camera; app.controls = controls;

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(innerWidth, innerHeight);
    labelRenderer.domElement.style.position = 'absolute';
    labelRenderer.domElement.style.top = '0';
    labelRenderer.domElement.style.pointerEvents = 'none';
    document.getElementById('labels').appendChild(labelRenderer.domElement);
    app.labelRenderer = labelRenderer;

    progress(52, '构建地形与城市基底…');
    const terrain = buildTerrain(terrainData, meta);
    terrain.userData.nx = terrainData.nx;
    terrain.userData.ny = terrainData.ny;
    terrain.userData.w = terrainData.w;
    terrain.userData.h = terrainData.h;
    scene.add(terrain);
    app.terrain = terrain;
    const sampleElev = terrain.userData.sampleElev;
    app.sampleElev = sampleElev;

    progress(64, '挤出建筑体块与夜景窗格…');
    const buildingsMesh = buildBuildings(buildings, meta, sampleElev);
    scene.add(buildingsMesh);
    app.buildings = buildingsMesh;

    progress(72, '铺设道路、水系与绿地…');
    const vectorsGroup = buildVectors(vectors, meta, sampleElev);
    scene.add(vectorsGroup);
    app.vectors = vectorsGroup;
    const trees = buildTrees(terrain, 950);
    scene.add(trees);
    app.trees = trees;

    const labels = buildLabels(meta, { p: buildings.p, n: buildings.n, h: buildings.h, b: buildings.b, roads: vectors.roads }, sampleElev);
    scene.add(labels);
    app.labels = labels;

    progress(80, '生成积水水面与雨幕…');
    const water = createWater(terrain, meta);
    scene.add(water.mesh);
    app.water = water;
    const rain = createRain(scene);
    app.rain = rain;

    progress(88, '接入 16 个积水监测站…');
    const sensorView = createSensors(sensors, meta, sampleElev, (s) => {
      app.selectedId = s.id;
      ui.openSensor(s);
    });
    scene.add(sensorView.group);
    app.sensorView = sensorView;

    progress(94, '装载暴雨情景与预警规则…');
    ui.init(app);
    ui.setScenarios(scenarios);
    await app.setScenario(scenarios[0].id, false);

    // 初始镜头
    camera.position.set(2350, 1900, 3100);
    controls.target.set(0, 0, 0);
    flyCamera(camera, controls, [1250, 1030, 1580], [-260, 20, 60], 2600);

    progress(100, '数字孪生底座就绪');
    setTimeout(() => {
      document.getElementById('loader').classList.add('done');
      setTimeout(() => {
        document.getElementById('loader').style.display = 'none';
        app.togglePlay(true);
      }, 700);
    }, 450);

    let last = performance.now();
    let acc = 0;
    const clock = { t: 0 };
    function loop(now) {
      const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
      last = now;
      clock.t += dt;
      controls.update();
      if (app.playing) {
        acc += dt * app.speed;
        if (acc >= 1.25) {
          acc = 0;
          const max = app.scenario.frames.length - 1;
          if (app.idx >= max) {
            app.togglePlay(false);
            ui.toast('情景推演结束 · 可拖动时间轴回看峰值过程');
          } else {
            app.setFrame(app.idx + 1);
          }
        }
      }
      // 水面 / 雨 / 建筑窗光随时间演化
      if (app.water?.mesh.visible) app.water.mesh.material.uniforms.uTime.value = clock.t;
      if (app.terrain) app.terrain.material.uniforms.uTime.value = clock.t;
      if (app.buildings) app.buildings.material.uniforms.uTime.value = clock.t;
      const rainRate = app.scenario ? app.scenario.frames[app.idx].rain : 0;
      app.rain.update(dt, camera, rainRate, app.layers.rain);
      if (app.sensorView) app.sensorView.update(app.frameSensors || [], app.selectedId, clock.t);
      updateCompass();
      app.labelRenderer.render(scene, camera);
      composer.render();
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  } catch (e) {
    console.error(e);
    loaderStep.innerHTML = `加载失败：${e.message}<br><span style="color:#ff9f43">请通过 node server.mjs 启动（不要直接双击 index.html）</span>`;
    loaderBar.style.background = '#ff4d5e';
  }
}

function updateCompass() {
  const n = document.getElementById('compass-needle');
  const alt = document.getElementById('cam-alt');
  if (!n || !app.camera) return;
  const dx = app.camera.position.x - app.controls.target.x;
  const dz = app.camera.position.z - app.controls.target.z;
  const ang = Math.atan2(dx, dz);
  n.style.transform = `rotate(${ang}rad)`;
  if (alt) alt.textContent = `H ${Math.round(app.camera.position.y)}m`;
}

app.setFrame = function (i) {
  if (!app.scenario) return;
  const max = app.scenario.frames.length - 1;
  app.idx = clamp(i, 0, max);
  const f = app.scenario.frames[app.idx];
  let depth = app._depthCache?.get(app.idx);
  if (!depth) {
    depth = b64ToU8(f.depth);
    if (!app._depthCache) app._depthCache = new Map();
    app._depthCache.set(app.idx, depth);
  }
  app.currentDepth = depth;
  if (app.layers.water) app.water.update(depth, performance.now() / 1000);
  else app.water.mesh.visible = false;
  app.frameSensors = app.scenario.sensors.map((ss) => ({ id: ss.id, depth: ss.series[app.idx] }));
  ui.renderFrame(app.scenario, app.idx);
};

app.setScenario = async function (id, userAction) {
  if (app.scenario?.id === id && !userAction) { /* 首次 */ }
  let scn = app._scenarios?.get(id);
  if (!scn) {
    const list = app.scenarios;
    const meta = list.find((x) => x.id === id) || list[0];
    scn = await fetchJSON(`./data/scenarios/${meta.id}.json`);
    if (!app._scenarios) app._scenarios = new Map();
    app._scenarios.set(id, scn);
  }
  app.togglePlay(false);
  app.scenario = scn;
  app.idx = 0;
  app._depthCache = new Map();
  app.frameSensors = scn.sensors.map((ss) => ({ id: ss.id, depth: ss.series[0] }));
  ui.setScenario(scn);
  if (userAction) {
    ui.toast(`已切换情景：${scn.name}`);
    app.togglePlay(true);
  }
};

app.togglePlay = function (force) {
  app.playing = force == null ? !app.playing : force;
  ui.setPlaying(app.playing);
};

app.setSpeed = function (s) { app.speed = s; };

app.selectSensor = function (id) { app.selectedId = id; };

app.flySensor = function (id) {
  const w = app.sensorView.getWorld(id);
  if (!w) return;
  const [x, y, z] = w;
  flyCamera(app.camera, app.controls, [x + 620, y + 520, z + 820], [x, y + 20, z], 1500);
};

app.flyPreset = function (key) {
  const c = app.camera, ctr = app.controls;
  if (key === 'overview') flyCamera(c, ctr, [0, 1380, 1900], [0, 0, 0], 1500);
  if (key === 'cbd') flyCamera(c, ctr, [-1450, 430, 2620], [-2056, 300, 1840], 1500);
  if (key === 'hqb') flyCamera(c, ctr, [1520, 440, 1480], [1133, 120, 843], 1500);
  if (key === 'lhs') flyCamera(c, ctr, [-1200, 520, 520], [-1542, 100, -487], 1500);
  if (key === 'hotspot') {
    const s = app.sensors.find((x) => x.id === app.selectedId) ||
      [...app.sensors].sort((a, b) => {
        const da = app.scenario.sensors.find((x) => x.id === a.id).series[app.idx];
        const db = app.scenario.sensors.find((x) => x.id === b.id).series[app.idx];
        return db - da;
      })[0];
    app.flySensor(s.id);
  }
};

app.toggleLayer = function (key, on) {
  app.layers[key] = on;
  if (key === 'water') {
    if (on && app.currentDepth) app.water.update(app.currentDepth, performance.now() / 1000);
    else app.water.mesh.visible = false;
  }
  if (key === 'buildings') app.buildings.visible = on;
  if (key === 'roads') {
    const r = app.vectors.getObjectByName('roads');
    if (r) r.visible = on;
    app.vectors.getObjectByName('green').visible = on;
  }
  if (key === 'sensors') app.sensorView.group.visible = on;
  if (key === 'rain') app.rain.setVisible(on);
  if (key === 'labels') {
    app.labels.visible = on;
    document.body.classList.toggle('hide-labels', !on);
  }
};

boot();
window.__app = app;

