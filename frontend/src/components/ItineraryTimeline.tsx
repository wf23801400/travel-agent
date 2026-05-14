import { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Sun, Sunrise, Sunset, Moon, Utensils, Bus, ShoppingBag, MapPin, DollarSign, RefreshCw, Copy, Image, Printer } from 'lucide-react';
import type { Itinerary, TimeSlot } from '../api/client';

interface Props {
  itinerary: Itinerary | null;
  onRefine?: (feedback: string) => Promise<void>;
  refining?: boolean;
  destination?: string;
}

function getTimeIcon(time: string) {
  const h = parseInt(time.split(':')[0]);
  if (h < 11) return <Sunrise className="w-4 h-4 text-amber-500" />;
  if (h < 14) return <Sun className="w-4 h-4 text-orange-500" />;
  if (h < 18) return <Sunset className="w-4 h-4 text-pink-500" />;
  return <Moon className="w-4 h-4 text-indigo-500" />;
}

function getActivityIcon(type: string) {
  switch (type) {
    case 'food': return <Utensils className="w-4 h-4 text-red-400" />;
    case 'transport': return <Bus className="w-4 h-4 text-blue-400" />;
    case 'shopping': return <ShoppingBag className="w-4 h-4 text-purple-400" />;
    default: return <MapPin className="w-4 h-4 text-green-400" />;
  }
}

function formatTime(time: string) {
  return time.slice(0, 5);
}

export default function ItineraryTimeline({ itinerary, onRefine, refining, destination }: Props) {
  const [feedback, setFeedback] = useState('');
  const [localRefining, setLocalRefining] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  if (!itinerary) return null;

  const isRefining = refining ?? localRefining;

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  };

  const handleRefine = async () => {
    if (!onRefine || !feedback.trim() || isRefining) return;
    setLocalRefining(true);
    try {
      await onRefine(feedback.trim());
      setFeedback('');
    } finally {
      setLocalRefining(false);
    }
  };

  const handleCopyText = async () => {
    if (!itinerary) return;
    const lines: string[] = [];
    lines.push('✈️ 行程计划');
    lines.push('');

    for (let di = 0; di < itinerary.days.length; di++) {
      const day = itinerary.days[di];
      lines.push(`第 ${di + 1} 天 · ${day.date}`);

      for (const slot of day.time_slots) {
        const time = `${slot.start_time.slice(0, 5)} - ${slot.end_time.slice(0, 5)}`;
        const typeLabel = slot.activity_type === 'food' ? '餐饮' :
          slot.activity_type === 'attraction' ? '景点' :
          slot.activity_type === 'transport' ? '交通' :
          slot.activity_type === 'shopping' ? '购物' : '其他';
        let line = `  ${time}  ${slot.activity_name} (${typeLabel})`;
        if (slot.location?.name) line += ` - ${slot.location.name}`;
        if (slot.cost > 0) line += ` - ¥${slot.cost}`;
        lines.push(line);
        if (slot.notes) lines.push(`    建议: ${slot.notes}`);
      }
      lines.push('');
    }

    lines.push(`💰 总预算: ¥${itinerary.total_budget_estimate.toLocaleString()}`);

    if (itinerary.tips.length > 0) {
      lines.push('');
      lines.push('💡 小贴士:');
      for (const tip of itinerary.tips) {
        lines.push(`  • ${tip}`);
      }
    }

    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      showToast('已复制到剪贴板');
    } catch {
      showToast('复制失败，请检查浏览器权限');
    }
  };

  const handleExportImage = async () => {
    if (!contentRef.current) return;
    try {
      const canvas = await html2canvas(contentRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
      });
      const today = new Date().toISOString().slice(0, 10);
      const dest = destination || '旅行';
      const filename = `行程计划-${dest}-${today}.png`;

      const link = document.createElement('a');
      link.download = filename;
      link.href = canvas.toDataURL('image/png');
      link.click();
      showToast(`图片已下载: ${filename}`);
    } catch {
      showToast('导出图片失败，请重试');
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        📋 行程安排
      </h2>

      {/* Export toolbar */}
      <div className="flex gap-2 mb-4 no-print">
        <button
          onClick={handleCopyText}
          className="px-3 py-2 rounded-xl text-sm font-medium border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 hover:border-gray-400 transition flex items-center gap-1.5"
        >
          <Copy className="w-4 h-4" />
          复制文本
        </button>
        <button
          onClick={handleExportImage}
          className="px-3 py-2 rounded-xl text-sm font-medium border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 hover:border-gray-400 transition flex items-center gap-1.5"
        >
          <Image className="w-4 h-4" />
          导出图片
        </button>
        <button
          onClick={handlePrint}
          className="px-3 py-2 rounded-xl text-sm font-medium border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 hover:border-gray-400 transition flex items-center gap-1.5"
        >
          <Printer className="w-4 h-4" />
          打印/PDF
        </button>
      </div>

      {/* Content for image export */}
      <div ref={contentRef}>
        {itinerary.days.map((day, di) => (
          <div key={di} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-4 last:mb-0">
            {/* 日期头 */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-5 py-3 border-b border-gray-100">
              <span className="font-semibold text-gray-800">
                📅 第 {di + 1} 天 · {day.date}
              </span>
            </div>

            {/* 时间线 */}
            <div className="p-5">
              <div className="relative">
                {day.time_slots.map((slot, si) => (
                  <TimeSlotCard key={si} slot={slot} index={si} isLast={si === day.time_slots.length - 1} />
                ))}
              </div>
            </div>
          </div>
        ))}

        {/* 预算汇总 */}
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl p-5 border border-amber-100">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-gray-800 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-amber-500" /> 总预算估算
            </span>
            <span className="text-2xl font-bold text-amber-600">
              ¥{itinerary.total_budget_estimate.toLocaleString()}
            </span>
          </div>

          {itinerary.tips.length > 0 && (
            <div className="mt-4 pt-4 border-t border-amber-200">
              <p className="text-sm font-medium text-gray-700 mb-2">💡 小贴士</p>
              <ul className="space-y-1">
                {itinerary.tips.map((tip, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-amber-500 mt-0.5">•</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* 修改行程 */}
      {onRefine && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 no-print">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            ✏️ 修改行程
          </h3>
          <textarea
            className="w-full border border-gray-200 rounded-xl p-3 text-sm text-gray-700 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-transparent transition"
            rows={3}
            placeholder="输入修改意见，如：第二天换成海鲜餐厅、第三天上午不要安排太紧..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={isRefining}
          />
          <button
            className="mt-3 w-full py-2.5 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
            onClick={handleRefine}
            disabled={isRefining || !feedback.trim()}
          >
            {isRefining ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                优化中...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                重新优化
              </>
            )}
          </button>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg text-sm z-50 animate-pulse">
          ✅ {toast}
        </div>
      )}
    </div>
  );
}

function TimeSlotCard({ slot, index, isLast }: { slot: TimeSlot; index: number; isLast: boolean }) {
  return (
    <div className="flex gap-4">
      {/* 时间线竖线 */}
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          {getTimeIcon(slot.start_time)}
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
      </div>

      {/* 内容 */}
      <div className="flex-1 pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-gray-400">
            {formatTime(slot.start_time)} - {formatTime(slot.end_time)}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 flex items-center gap-1">
            {getActivityIcon(slot.activity_type)}
            {slot.activity_type === 'food' ? '餐饮' :
             slot.activity_type === 'attraction' ? '景点' :
             slot.activity_type === 'transport' ? '交通' :
             slot.activity_type === 'shopping' ? '购物' : '其他'}
          </span>
        </div>
        <p className="font-medium text-gray-800">{slot.activity_name}</p>
        {slot.location && (
          <p className="text-xs text-gray-400 mt-0.5">{slot.location.name}</p>
        )}
        {slot.cost > 0 && (
          <p className="text-xs text-amber-500 mt-0.5">¥{slot.cost}</p>
        )}
        {slot.notes && (
          <p className="text-xs text-gray-400 mt-0.5 italic">{slot.notes}</p>
        )}
      </div>
    </div>
  );
}
