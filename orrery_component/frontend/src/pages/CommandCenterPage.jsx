import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import GalaxyCanvas from '../components/GalaxyCanvas.jsx';
import StatusPanel from '../components/StatusPanel.jsx';
import OrbitalControlsPanel from '../components/OrbitalControlsPanel.jsx';
import PizInfoPanel from '../components/PizInfoPanel.jsx';
import MissionControl from '../components/MissionControl.jsx';
import SatelliteFleet from '../components/SatelliteFleet.jsx';
import DiscoveryCollection from '../components/DiscoveryCollection.jsx';
import ConsolePanel from '../components/ConsolePanel.jsx';
import TimeControlBar from '../components/TimeControlBar.jsx';
import PlanetModal from '../components/PlanetModal.jsx';
import { OrreryEngine } from '../lib/orreryEngine.js';

const DEFAULT_UI = {
  priorityCount: 0,
  discoveryCount: 0,
  dataStatus: 'LIVE',
  dataSource: 'NASA Exoplanet Archive',
  solverName: 'kepler_newton',
  catalogVisible: 0,
  catalogTotal: 0,
  trackingTarget: 'OFF',
  simDateText: '-',
  simSpeedText: '1 day/second',
  timeScale: 1,
};

const DEFAULT_FILTERS = {
  showConfirmed: true,
  showHabitable: true,
  radiusMin: 0.3,
  radiusMax: 20.0,
  periodMin: 1,
  periodMax: 1200,
};

function CommandCenterPage() {
  const canvasRef = useRef(null);
  const engineRef = useRef(null);
  const consoleIdRef = useRef(0);

  const [ui, setUi] = useState(DEFAULT_UI);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selectedPiz, setSelectedPiz] = useState(null);
  const [selectedSatellite, setSelectedSatellite] = useState(0);
  const [discoveries, setDiscoveries] = useState([]);
  const [councilLoading, setCouncilLoading] = useState(false);
  const [consoleLines, setConsoleLines] = useState([
    { id: 1, type: 'command', message: 'ATLAS AI: System initialized. Welcome, Director.' },
    { id: 2, type: 'info', message: 'Deep space sensors active. Awaiting real-data synchronization.' },
  ]);
  const [modalState, setModalState] = useState({ open: false, details: null });

  const appendLog = useCallback((entry) => {
    consoleIdRef.current += 1;
    const nextLine = { id: consoleIdRef.current, ...entry };
    setConsoleLines((prev) => {
      const merged = [...prev, nextLine];
      return merged.slice(-120);
    });
  }, []);

  const requestCouncilBrief = useCallback(async (reason, extra = {}) => {
    if (councilLoading) return;
    setCouncilLoading(true);
    try {
      const response = await fetch('/api/council/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'discovery',
          player_goal: 'find potentially habitable worlds',
          selected_planet_id: extra.selectedPlanetId || null,
          selected_piz_id: selectedPiz?.id || null,
          filters,
          challenge_state: { active: false, objective: '', progress: 0 },
          recent_actions: [reason],
        }),
      });

      if (!response.ok) {
        throw new Error(`Council API unavailable (${response.status})`);
      }

      const payload = await response.json();
      appendLog({ type: 'command', message: `COUNCIL: ${payload.headline}` });

      if (payload.primary_recommendation?.action && payload.primary_recommendation?.target_id) {
        appendLog({
          type: 'info',
          message: `Recommend: ${payload.primary_recommendation.action} -> ${payload.primary_recommendation.target_id}`,
        });
      }

      (payload.council_votes || []).slice(0, 3).forEach((vote) => {
        const prefix = vote.stance === 'caution' ? '⚠' : '✓';
        appendLog({
          type: vote.stance === 'caution' ? 'warning' : 'info',
          message: `${prefix} ${vote.agent} (${Math.round((vote.confidence || 0) * 100)}%): ${vote.message}`,
        });
      });
    } catch (error) {
      appendLog({ type: 'warning', message: `Council brief failed: ${error.message}` });
    } finally {
      setCouncilLoading(false);
    }
  }, [appendLog, councilLoading, filters, selectedPiz]);

  const openPlanetDetails = useCallback(async (planetData) => {
    try {
      const encoded = encodeURIComponent(planetData.id);
      const response = await fetch(`/api/planet/${encoded}`);
      if (!response.ok) {
        throw new Error(`Planet details unavailable (${response.status})`);
      }
      const details = await response.json();
      setModalState({ open: true, details });
    } catch (error) {
      appendLog({ type: 'warning', message: `Unable to load full details for ${planetData.id}: ${error.message}` });
      setModalState({
        open: true,
        details: {
          id: planetData.id,
          star: planetData.star || 'Unknown',
          mass: `${Number(planetData.mass || 1).toFixed(2)} Earth masses`,
          radius: `${Number(planetData.radius || 1).toFixed(2)} Earth radii`,
          period: `${Number(planetData.period || 0).toFixed(2)} days`,
          temp: `${Math.round(Number(planetData.temp || 300))}K`,
          habitable: Boolean(planetData.habitable),
        },
      });
    }
  }, [appendLog]);

  useEffect(() => {
    if (!canvasRef.current) return undefined;

    const engine = new OrreryEngine({
      mountElement: canvasRef.current,
      callbacks: {
        onStateChange: (partial) => {
          setUi((prev) => ({ ...prev, ...partial }));
        },
        onLog: appendLog,
        onPizSelected: (piz) => setSelectedPiz(piz),
        onDiscovery: (item) => {
          setDiscoveries((prev) => {
            if (prev.some((entry) => entry.id === item.id)) return prev;
            return [...prev, item];
          });
        },
        onOpenPlanet: openPlanetDetails,
      },
    });

    engineRef.current = engine;

    engine.init().catch((error) => {
      appendLog({ type: 'warning', message: `Engine init failed: ${error.message}` });
    });

    return () => {
      engine.destroy();
      engineRef.current = null;
    };
  }, [appendLog, openPlanetDetails]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
      if (activeTag === 'input' || activeTag === 'textarea') return;
      if (!engineRef.current) return;

      const key = String(event.key || '').toLowerCase();
      if (key === 't') {
        event.preventDefault();
        engineRef.current.setTrackingMode(true);
      } else if (key === 'u') {
        event.preventDefault();
        engineRef.current.setTrackingMode(false);
      } else if (key === 'q') {
        event.preventDefault();
        engineRef.current.stepTimeScale(-1);
      } else if (key === 'e') {
        event.preventDefault();
        engineRef.current.stepTimeScale(1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleFilterChange = useCallback((patch) => {
    setFilters((prev) => {
      const next = { ...prev, ...patch };

      if (next.radiusMin > next.radiusMax) {
        if (typeof patch.radiusMin !== 'undefined') {
          next.radiusMax = next.radiusMin;
        } else {
          next.radiusMin = next.radiusMax;
        }
      }

      if (next.periodMin > next.periodMax) {
        if (typeof patch.periodMin !== 'undefined') {
          next.periodMax = next.periodMin;
        } else {
          next.periodMin = next.periodMax;
        }
      }

      engineRef.current?.setFilters(next);
      return next;
    });
    requestCouncilBrief('filter_adjusted');
  }, [requestCouncilBrief]);

  const handleSelectSatellite = useCallback((index) => {
    setSelectedSatellite(index);
    engineRef.current?.selectSatellite(index);
  }, []);

  const handleScan = useCallback((pattern) => {
    appendLog({ type: 'command', message: `Initiating ${pattern.toUpperCase()} scan protocol...` });
    engineRef.current?.startScan(pattern);
    requestCouncilBrief(`${pattern}_scan`);
  }, [appendLog, requestCouncilBrief]);

  const handleSpeedSelect = useCallback((value) => {
    engineRef.current?.setTimeScale(value, true);
  }, []);

  const handleResetTime = useCallback(() => {
    engineRef.current?.resetTime();
  }, []);

  const handleTrackEnable = useCallback(() => {
    engineRef.current?.setTrackingMode(true);
  }, []);

  const handleTrackDisable = useCallback(() => {
    engineRef.current?.setTrackingMode(false);
  }, []);

  const missionVisible = useMemo(() => Boolean(selectedPiz), [selectedPiz]);

  return (
    <div className="command-layout">
      <GalaxyCanvas canvasRef={canvasRef} />

      <div className="overlay-grid">
        <StatusPanel priorityCount={ui.priorityCount} discoveryCount={ui.discoveryCount} />
        <OrbitalControlsPanel
          ui={ui}
          filters={filters}
          onFilterChange={handleFilterChange}
          onTrackEnable={handleTrackEnable}
          onTrackDisable={handleTrackDisable}
        />
        <PizInfoPanel selectedPiz={selectedPiz} />
        <MissionControl visible={missionVisible} onScan={handleScan} />
        <SatelliteFleet selectedSatellite={selectedSatellite} onSelectSatellite={handleSelectSatellite} />
        <DiscoveryCollection discoveries={discoveries} onOpenPlanet={openPlanetDetails} />
        <ConsolePanel lines={consoleLines} />
        <TimeControlBar
          simDateText={ui.simDateText}
          simSpeedText={ui.simSpeedText}
          timeScale={ui.timeScale}
          onSpeedSelect={handleSpeedSelect}
          onResetTime={handleResetTime}
        />
      </div>

      <PlanetModal
        open={modalState.open}
        details={modalState.details}
        onClose={() => setModalState({ open: false, details: null })}
      />
    </div>
  );
}

export default CommandCenterPage;
