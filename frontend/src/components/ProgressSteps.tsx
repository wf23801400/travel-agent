import { useMemo } from 'react';
import { MapPin, Sun, Search, DollarSign, Brain, CheckCircle, Loader2 } from 'lucide-react';

export interface ProgressState {
  step: string;
  label: string;
}

interface Props {
  currentStep: string | null;
}

const ALL_STEPS = [
  { id: 'parse_input', icon: MapPin, label: '解析目的地' },
  { id: 'fetch_weather', icon: Sun, label: '查询天气' },
  { id: 'search_poi', icon: Search, label: '搜索景点' },
  { id: 'estimate_budget', icon: DollarSign, label: '估算预算' },
  { id: 'assemble_context', icon: Loader2, label: '整合信息' },
  { id: 'llm_plan', icon: Brain, label: 'AI 生成行程' },
  { id: 'validate_output', icon: CheckCircle, label: '校验完善' },
];

export default function ProgressSteps({ currentStep }: Props) {
  const currentIdx = useMemo(() => {
    if (!currentStep) return -1;
    const idx = ALL_STEPS.findIndex((s) => s.id === currentStep);
    return idx >= 0 ? idx : ALL_STEPS.length;
  }, [currentStep]);

  if (!currentStep) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
        正在规划行程...
      </h3>

      <div className="space-y-3">
        {ALL_STEPS.map((step, i) => {
          const isDone = i < currentIdx;
          const isCurrent = i === currentIdx;
          const isPending = i > currentIdx;

          return (
            <div key={step.id} className="flex items-center gap-3">
              {/* 状态图标 */}
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all ${
                  isDone
                    ? 'bg-green-100 text-green-600'
                    : isCurrent
                    ? 'bg-blue-100 text-blue-600 ring-2 ring-blue-300 ring-offset-1'
                    : 'bg-gray-50 text-gray-300'
                }`}
              >
                {isDone ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <step.icon className={`w-4 h-4 ${isCurrent ? 'animate-pulse' : ''}`} />
                )}
              </div>

              {/* 文字 */}
              <span
                className={`text-sm transition-colors ${
                  isDone
                    ? 'text-green-600'
                    : isCurrent
                    ? 'text-blue-700 font-medium'
                    : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>

              {/* 当前步骤的状态文字 */}
              {isCurrent && (
                <span className="text-xs text-blue-400 ml-auto animate-pulse">
                  进行中...
                </span>
              )}
              {isDone && (
                <span className="text-xs text-green-400 ml-auto">✓</span>
              )}
            </div>
          );
        })}
      </div>

      {/* 当前步骤详情 */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-500 text-center">
          {ALL_STEPS.find((s) => s.id === currentStep)?.label || '处理中...'}
        </p>
      </div>
    </div>
  );
}
