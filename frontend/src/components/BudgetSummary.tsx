import type { Itinerary } from '../api/client';

interface Props {
  itinerary: Itinerary | null;
}

// 模拟分项数据（后端目前返回总预算，细项后续由 LLM 提供）
const MOCK_BREAKDOWN = [
  { label: '住宿', percent: 40, color: 'bg-blue-500' },
  { label: '餐饮', percent: 25, color: 'bg-green-500' },
  { label: '交通', percent: 15, color: 'bg-amber-500' },
  { label: '景点', percent: 10, color: 'bg-purple-500' },
  { label: '购物', percent: 7, color: 'bg-pink-500' },
  { label: '其他', percent: 3, color: 'bg-gray-400' },
];

export default function BudgetSummary({ itinerary }: Props) {
  if (!itinerary) return null;

  const total = itinerary.total_budget_estimate;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <h3 className="font-semibold text-gray-800 mb-4">💰 预算概览</h3>

      <div className="text-center mb-5">
        <p className="text-3xl font-bold text-gray-800">¥{total.toLocaleString()}</p>
        <p className="text-xs text-gray-400 mt-1">总预算估算</p>
      </div>

      {/* 堆叠进度条 */}
      <div className="h-3 bg-gray-100 rounded-full overflow-hidden flex mb-4">
        {MOCK_BREAKDOWN.map((item, i) => (
          <div
            key={i}
            className={`${item.color} h-full transition-all`}
            style={{ width: `${item.percent}%` }}
          />
        ))}
      </div>

      {/* 图例 */}
      <div className="grid grid-cols-2 gap-2">
        {MOCK_BREAKDOWN.map((item, i) => (
          <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
            <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
            <span>{item.label}</span>
            <span className="text-gray-400 ml-auto">{item.percent}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
