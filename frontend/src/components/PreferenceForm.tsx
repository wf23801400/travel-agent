import { useState } from 'react';
import { MapPin, Calendar, Users, Wallet, Gauge, Heart } from 'lucide-react';

interface FormData {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget_amount: number | '';
  pace: 'relaxed' | 'moderate' | 'intensive';
  interests: string[];
}

interface Props {
  onSubmit: (data: FormData) => void;
  loading: boolean;
}

const INTEREST_OPTIONS = ['美食', '历史', '自然', '购物', '艺术', '户外'];

const PACE_OPTIONS = [
  { value: 'relaxed' as const, label: '🌿 宽松', desc: '慢慢逛' },
  { value: 'moderate' as const, label: '🚶 适中', desc: '正常节奏' },
  { value: 'intensive' as const, label: '⚡ 紧凑', desc: '多跑几个点' },
];

export default function PreferenceForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<FormData>({
    origin: '',
    destination: '',
    start_date: '',
    end_date: '',
    travelers: 1,
    budget_amount: '',
    pace: 'moderate',
    interests: [],
  });

  const toggleInterest = (tag: string) => {
    setForm((f) => ({
      ...f,
      interests: f.interests.includes(tag)
        ? f.interests.filter((t) => t !== tag)
        : [...f.interests, tag],
    }));
  };

  const handleSubmit = () => {
    onSubmit(form);
  };

  return (
    <div className="space-y-6">
      {/* 出发地 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
          <MapPin className="w-4 h-4 text-emerald-500" /> 出发地
        </label>
        <input
          type="text"
          placeholder="输入出发地，如：北京、上海站、朝阳路45号"
          value={form.origin}
          onChange={(e) => setForm({ ...form, origin: e.target.value })}
          className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-emerald-400 focus:border-transparent outline-none transition"
        />
      </div>

      {/* 目的地 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
          <MapPin className="w-4 h-4 text-blue-500" /> 目的地
        </label>
        <input
          type="text"
          placeholder="输入目的地，如：东京、故宫、张家界国家森林公园"
          value={form.destination}
          onChange={(e) => setForm({ ...form, destination: e.target.value })}
          className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition"
        />
      </div>

      {/* 日期 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
            <Calendar className="w-4 h-4 text-blue-500" /> 开始日期
          </label>
          <input
            type="date"
            value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition"
          />
        </div>
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
            <Calendar className="w-4 h-4 text-blue-500" /> 结束日期
          </label>
          <input
            type="date"
            value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition"
          />
        </div>
      </div>

      {/* 人数 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
          <Users className="w-4 h-4 text-blue-500" /> 出行人数
        </label>
        <input
          type="number"
          min={1}
          value={form.travelers}
          onChange={(e) => setForm({ ...form, travelers: parseInt(e.target.value) || 1 })}
          className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition"
        />
      </div>

      {/* 预算金额 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1.5">
          <Wallet className="w-4 h-4 text-blue-500" /> 预算总额（元）
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">¥</span>
          <input
            type="number"
            min={0}
            step={500}
            placeholder="不填则自动估算"
            value={form.budget_amount}
            onChange={(e) => setForm({ ...form, budget_amount: e.target.value ? parseFloat(e.target.value) : '' })}
            className="w-full pl-8 pr-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-400 focus:border-transparent outline-none transition"
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">填写总预算，AI 将据此合理安排每日开销</p>
      </div>

      {/* 节奏 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Gauge className="w-4 h-4 text-blue-500" /> 行程节奏
        </label>
        <div className="grid grid-cols-3 gap-2">
          {PACE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setForm({ ...form, pace: opt.value })}
              className={`p-3 rounded-xl border-2 text-center transition ${
                form.pace === opt.value
                  ? 'border-green-500 bg-green-50 text-green-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }`}
            >
              <div className="text-sm font-medium">{opt.label}</div>
              <div className="text-xs mt-0.5">{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 兴趣标签 */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Heart className="w-4 h-4 text-blue-500" /> 兴趣偏好
        </label>
        <div className="flex flex-wrap gap-2">
          {INTEREST_OPTIONS.map((tag) => (
            <button
              key={tag}
              onClick={() => toggleInterest(tag)}
              className={`px-4 py-1.5 rounded-full text-sm border transition ${
                form.interests.includes(tag)
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* 提交 */}
      <button
        onClick={handleSubmit}
        disabled={loading || !form.destination || !form.start_date || !form.end_date}
        className="w-full py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium rounded-xl hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2 shadow-lg shadow-blue-200"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            规划中...
          </span>
        ) : (
          <span className="flex items-center gap-2">✨ 生成行程</span>
        )}
      </button>
    </div>
  );
}
