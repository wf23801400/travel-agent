import { useState, useRef, useCallback } from 'react';
import PreferenceForm from './components/PreferenceForm';
import ItineraryTimeline from './components/ItineraryTimeline';
import TravelMap from './components/TravelMap';
import BudgetSummary from './components/BudgetSummary';
import ProgressSteps from './components/ProgressSteps';
import { planTrip, refinePlan, type Itinerary, type TravelRequest } from './api/client';

export default function App() {
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [originalRequest, setOriginalRequest] = useState<TravelRequest | null>(null);
  const [loading, setLoading] = useState(false);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(async (form: {
    origin: string;
    destination: string;
    start_date: string;
    end_date: string;
    travelers: number;
    budget_amount: number | '';
    pace: 'relaxed' | 'moderate' | 'intensive';
    interests: string[];
  }) => {
    setLoading(true);
    setError(null);
    setItinerary(null);
    setCurrentStep('parse_input');

    const request: TravelRequest = {
      ...form,
      budget_amount: form.budget_amount || undefined,
      dietary_restrictions: [],
    };
    setOriginalRequest(request);

    // 使用 SSE 流式获取进度
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch('http://localhost:8000/api/plan/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error('无法读取响应流');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          const eventLine = line.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const l of eventLine) {
            if (l.startsWith('event: ')) eventType = l.slice(7);
            if (l.startsWith('data: ')) dataStr = l.slice(6);
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (eventType === 'progress') {
              setCurrentStep(data.step);
            } else if (eventType === 'error') {
              setError(data.error || '生成过程出错');
              setLoading(false);
              setCurrentStep(null);
              return;
            } else if (eventType === 'complete') {
              setItinerary(data.itinerary as Itinerary);
              setLoading(false);
              setCurrentStep(null);
              return;
            }
          } catch {
            // 忽略解析错误
          }
        }
      }

      // 流结束但没收到 complete — 降级用普通 POST
      const result = await planTrip(request);
      setItinerary(result);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      // SSE 失败降级到普通 POST
      try {
        const result = await planTrip(request);
        setItinerary(result);
      } catch (fallbackErr) {
        setError(fallbackErr instanceof Error ? fallbackErr.message : '规划失败，请检查后端是否启动');
      }
    } finally {
      setLoading(false);
      setCurrentStep(null);
      abortRef.current = null;
    }
  }, []);

  const handleRefine = async (feedback: string) => {
    if (!originalRequest) return;
    setRefining(true);
    setError(null);
    try {
      const result = await refinePlan(originalRequest, feedback);
      setItinerary(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '优化失败，请检查后端是否启动');
    } finally {
      setRefining(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* 顶栏 */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✈️</span>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              旅游规划师
            </h1>
          </div>
          <p className="text-sm text-gray-400">AI 驱动的智能行程规划</p>
        </div>
      </header>

      {/* 主体 */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧：表单 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sticky top-24">
              <h2 className="text-lg font-semibold text-gray-800 mb-5 flex items-center gap-2">
                🎯 告诉我你的旅行偏好
              </h2>
              <PreferenceForm onSubmit={handleSubmit} loading={loading} />
            </div>
          </div>

          {/* 右侧：进度/行程/地图 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 加载进度 */}
            {loading && currentStep && (
              <ProgressSteps currentStep={currentStep} />
            )}

            {/* 地图 */}
            {itinerary && (
              <div className="h-[400px]">
                <TravelMap itinerary={itinerary} />
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-red-700 text-sm">
                ❌ {error}
              </div>
            )}

            {/* 行程时间线 */}
            {itinerary && <ItineraryTimeline itinerary={itinerary} onRefine={handleRefine} refining={refining} destination={originalRequest?.destination} />}

            {/* 预算卡片 */}
            {itinerary && (
              <div className="lg:hidden">
                <BudgetSummary itinerary={itinerary} />
              </div>
            )}

            {/* 空态 */}
            {!itinerary && !loading && !error && (
              <div className="h-[400px] flex items-center justify-center bg-white rounded-2xl border border-gray-100">
                <div className="text-center">
                  <div className="text-6xl mb-4">🗺️</div>
                  <p className="text-gray-400 text-lg">在左侧输入旅行偏好</p>
                  <p className="text-gray-300 text-sm mt-1">点击「生成行程」开始规划</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
