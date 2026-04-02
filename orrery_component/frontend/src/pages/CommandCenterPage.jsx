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
import CouncilChatPanel from '../components/CouncilChatPanel.jsx';
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

const LEFT_DOCK_TABS = {
  STATUS: 'status',
  CONTROLS: 'controls',
};

const RIGHT_DOCK_TABS = {
  INTEL: 'intel',
  FLEET: 'fleet',
  DISCOVERY: 'discovery',
};

function CommandCenterPage() {
  const canvasRef = useRef(null);
  const engineRef = useRef(null);
  const consoleIdRef = useRef(0);
  const chatIdRef = useRef(0);

  const [ui, setUi] = useState(DEFAULT_UI);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selectedPiz, setSelectedPiz] = useState(null);
  const [pizCatalog, setPizCatalog] = useState([]);
  const [selectedSatellite, setSelectedSatellite] = useState(0);
  const [discoveries, setDiscoveries] = useState([]);
  const [councilLoading, setCouncilLoading] = useState(false);
  const [leftDockTab, setLeftDockTab] = useState(LEFT_DOCK_TABS.CONTROLS);
  const [rightDockTab, setRightDockTab] = useState(RIGHT_DOCK_TABS.INTEL);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      text: 'Council channel online. Ask for comparison, risk analysis, or next mission action.',
    },
  ]);
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
      return merged.slice(-140);
    });
  }, []);

  const appendChatMessage = useCallback((role, text) => {
    chatIdRef.current += 1;
    setChatMessages((prev) => ([...prev, { id: chatIdRef.current, role, text }]));
  }, []);

  const fetchCouncilPayload = useCallback(async ({ reason, extra = {}, playerGoal, recentActions } = {}) => {
    const response = await fetch('/api/council/respond', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: 'discovery',
        player_goal: playerGoal || 'find potentially habitable worlds',
        selected_planet_id: extra.selectedPlanetId || null,
        selected_piz_id: extra.selectedPizId || selectedPiz?.id || null,
        filters,
        challenge_state: { active: false, objective: '', progress: 0 },
        recent_actions: recentActions || [reason || 'manual_brief'],
      }),
    });

    if (!response.ok) {
      throw new Error(`Council API unavailable (${response.status})`);
    }

    return response.json();
  }, [filters, selectedPiz]);

  const requestCouncilBrief = useCallback(async (reason, extra = {}) => {
    if (councilLoading) return null;
    setCouncilLoading(true);

    try {
      const payload = await fetchCouncilPayload({
        reason,
        extra,
        recentActions: [reason],
      });

      appendLog({ type: 'command', message: `COUNCIL: ${payload.headline}` });

      if (payload.primary_recommendation?.action && payload.primary_recommendation?.target_id) {
        appendLog({
          type: 'info',
          message: `Recommend: ${payload.primary_recommendation.action} -> ${payload.primary_recommendation.target_id}`,
        });
      }

      (payload.council_votes || []).slice(0, 4).forEach((vote) => {
        const isRiskStance = vote.stance === 'caution' || vote.stance === 'oppose';
        const prefix = vote.stance === 'oppose' ? '✖' : (vote.stance === 'caution' ? '⚠' : '✓');
        appendLog({
          type: isRiskStance ? 'warning' : 'info',
          message: `${prefix} ${vote.agent} (${Math.round((vote.confidence || 0) * 100)}%): ${vote.message}`,
        });
      });

      return payload;
    } catch (error) {
      appendLog({ type: 'warning', message: `Council brief failed: ${error.message}` });
      return null;
    } finally {
      setCouncilLoading(false);
    }
  }, [appendLog, councilLoading, fetchCouncilPayload]);

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
        onPizCatalog: (items) => setPizCatalog(items || []),
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
      } else if (key === '=' || key === '+') {
        event.preventDefault();
        engineRef.current.zoomStep(-1);
      } else if (key === '-' || key === '_') {
        event.preventDefault();
        engineRef.current.zoomStep(1);
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

  const handleSelectPizFromPanel = useCallback((pizId) => {
    const selected = engineRef.current?.selectPizById(pizId);
    if (selected) {
      setRightDockTab(RIGHT_DOCK_TABS.INTEL);
      requestCouncilBrief('piz_selected', { selectedPizId: pizId });
    }
  }, [requestCouncilBrief]);

  const handleScan = useCallback((pattern) => {
    appendLog({ type: 'command', message: `Initiating ${pattern.toUpperCase()} scan protocol...` });
    engineRef.current?.startScan(pattern);
    requestCouncilBrief(`${pattern}_scan`);
  }, [appendLog, requestCouncilBrief]);

  const handleSendChat = useCallback(async () => {
    const query = chatInput.trim();
    if (!query || councilLoading) return;

    setChatInput('');
    appendChatMessage('user', query);
    setCouncilLoading(true);

    try {
      const payload = await fetchCouncilPayload({
        reason: 'chat_query',
        playerGoal: query,
        recentActions: [`chat_query:${query}`],
      });

      const voteDigest = (payload.council_votes || [])
        .slice(0, 4)
        .map((vote) => `${vote.agent}:${vote.stance}`)
        .join(' | ');

      const answer = [
        payload.headline,
        payload.primary_recommendation?.reason || '',
        voteDigest ? `Votes -> ${voteDigest}` : '',
      ].filter(Boolean).join('\n');

      appendChatMessage('assistant', answer);
      appendLog({ type: 'info', message: `Chat answered by council (${(payload.council_votes || []).length} roles).` });
    } catch (error) {
      appendChatMessage('assistant', `Council chat failed: ${error.message}`);
      appendLog({ type: 'warning', message: `Council chat failed: ${error.message}` });
    } finally {
      setCouncilLoading(false);
    }
  }, [appendChatMessage, appendLog, chatInput, councilLoading, fetchCouncilPayload]);

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

  const handleZoomIn = useCallback(() => {
    engineRef.current?.zoomStep(-1);
  }, []);

  const handleZoomOut = useCallback(() => {
    engineRef.current?.zoomStep(1);
  }, []);

  const missionVisible = useMemo(() => Boolean(selectedPiz), [selectedPiz]);

  useEffect(() => {
    if (selectedPiz) {
      setRightDockTab(RIGHT_DOCK_TABS.INTEL);
    }
  }, [selectedPiz]);

  return (
    <div className="command-layout">
      <GalaxyCanvas canvasRef={canvasRef} />

      <div className="overlay-shell">
        <aside className="dock dock-left">
          <div className="dock-toolbar">
            <span className="dock-title">Operations</span>
            <div className="dock-switches">
              <button
                type="button"
                className={`dock-switch ${leftDockTab === LEFT_DOCK_TABS.STATUS ? 'active' : ''}`}
                onClick={() => setLeftDockTab(LEFT_DOCK_TABS.STATUS)}
              >
                Status
              </button>
              <button
                type="button"
                className={`dock-switch ${leftDockTab === LEFT_DOCK_TABS.CONTROLS ? 'active' : ''}`}
                onClick={() => setLeftDockTab(LEFT_DOCK_TABS.CONTROLS)}
              >
                Orbit
              </button>
            </div>
          </div>
          <div className="dock-content">
            {leftDockTab === LEFT_DOCK_TABS.STATUS ? (
              <StatusPanel priorityCount={ui.priorityCount} discoveryCount={ui.discoveryCount} />
            ) : (
              <OrbitalControlsPanel
                ui={ui}
                filters={filters}
                onFilterChange={handleFilterChange}
                onTrackEnable={handleTrackEnable}
                onTrackDisable={handleTrackDisable}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
              />
            )}
          </div>
        </aside>

        <section className="center-stack">
          <MissionControl visible={missionVisible} onScan={handleScan} />
          <div className="stage-buffer" aria-hidden="true" />
          <div className="center-bottom">
            <div className="ops-workspace">
              <ConsolePanel lines={consoleLines} />
              <CouncilChatPanel
                messages={chatMessages}
                input={chatInput}
                onInputChange={setChatInput}
                onSend={handleSendChat}
                loading={councilLoading}
              />
            </div>
            <TimeControlBar
              simDateText={ui.simDateText}
              simSpeedText={ui.simSpeedText}
              timeScale={ui.timeScale}
              onSpeedSelect={handleSpeedSelect}
              onResetTime={handleResetTime}
            />
          </div>
        </section>

        <aside className="dock dock-right">
          <div className="dock-toolbar">
            <span className="dock-title">Intelligence</span>
            <div className="dock-switches">
              <button
                type="button"
                className={`dock-switch ${rightDockTab === RIGHT_DOCK_TABS.INTEL ? 'active' : ''}`}
                onClick={() => setRightDockTab(RIGHT_DOCK_TABS.INTEL)}
              >
                PIZ
              </button>
              <button
                type="button"
                className={`dock-switch ${rightDockTab === RIGHT_DOCK_TABS.FLEET ? 'active' : ''}`}
                onClick={() => setRightDockTab(RIGHT_DOCK_TABS.FLEET)}
              >
                Fleet
              </button>
              <button
                type="button"
                className={`dock-switch ${rightDockTab === RIGHT_DOCK_TABS.DISCOVERY ? 'active' : ''}`}
                onClick={() => setRightDockTab(RIGHT_DOCK_TABS.DISCOVERY)}
              >
                Discoveries
              </button>
            </div>
          </div>
          <div className="dock-content">
            {rightDockTab === RIGHT_DOCK_TABS.INTEL ? (
              <PizInfoPanel selectedPiz={selectedPiz} pizCatalog={pizCatalog} onSelectPiz={handleSelectPizFromPanel} />
            ) : null}
            {rightDockTab === RIGHT_DOCK_TABS.FLEET ? (
              <SatelliteFleet selectedSatellite={selectedSatellite} onSelectSatellite={handleSelectSatellite} />
            ) : null}
            {rightDockTab === RIGHT_DOCK_TABS.DISCOVERY ? (
              <DiscoveryCollection discoveries={discoveries} onOpenPlanet={openPlanetDetails} />
            ) : null}
          </div>
        </aside>
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
