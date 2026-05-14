import { useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Itinerary } from '../api/client';

// 修复 Leaflet 默认图标路径问题
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

// 每天不同颜色
const DAY_COLORS = [
  '#3b82f6', // 蓝
  '#ef4444', // 红
  '#22c55e', // 绿
  '#f59e0b', // 橙
  '#a855f7', // 紫
  '#ec4899', // 粉
  '#14b8a6', // 青
  '#64748b', // 灰
];

const DAY_LABELS = ['第1天', '第2天', '第3天', '第4天', '第5天', '第6天', '第7天', '第8天'];

interface MapPoint {
  name: string;
  lat: number;
  lng: number;
  day: number;
  type: string;
  index: number; // 当天内排序
}

interface Props {
  itinerary: Itinerary | null;
}

// 地图自适应
function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useMemo(() => {
    if (points.length === 0) return;
    const bounds = L.latLngBounds(
      points.map((p) => [p.lat, p.lng] as [number, number])
    );
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [60, 60] });
    }
  }, [points, map]);
  return null;
}

// 生成带数字的自定义图标
function createNumberedIcon(index: number, color: string) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width: 28px; height: 28px;
      background: ${color};
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: bold;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      border: 2px solid white;
    ">${index}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

const typeColors: Record<string, string> = {
  food: '#ef4444',
  attraction: '#22c55e',
  transport: '#3b82f6',
  shopping: '#a855f7',
  rest: '#f59e0b',
  accommodation: '#14b8a6',
};

const typeLabels: Record<string, string> = {
  food: '🍜 餐饮',
  attraction: '🏛️ 景点',
  transport: '🚇 交通',
  shopping: '🛍️ 购物',
  rest: '😴 休息',
  accommodation: '🏨 住宿',
  other: '📍 其他',
};

export default function TravelMap({ itinerary }: Props) {
  // 按天整理坐标点
  const dayPoints = useMemo(() => {
    if (!itinerary) return new Map<number, MapPoint[]>();

    const map = new Map<number, MapPoint[]>();
    itinerary.days.forEach((day, di) => {
      const points = day.time_slots
        .filter((slot) => slot.location?.lat && slot.location?.lng)
        .map((slot, si) => ({
          name: slot.location!.name,
          lat: slot.location!.lat,
          lng: slot.location!.lng,
          day: di + 1,
          type: slot.activity_type,
          index: si + 1,
        }));
      if (points.length > 0) {
        map.set(di + 1, points);
      }
    });
    return map;
  }, [itinerary]);

  const allPoints = useMemo(() => {
    const pts: MapPoint[] = [];
    dayPoints.forEach((points) => pts.push(...points));
    return pts;
  }, [dayPoints]);

  const dayKeys = useMemo(() => [...dayPoints.keys()].sort(), [dayPoints]);

  if (!itinerary || allPoints.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-2xl border border-gray-200">
        <div className="text-center text-gray-400">
          <div className="text-4xl mb-2">🗺️</div>
          <p className="text-sm">生成行程后，景点将显示在地图上</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full rounded-2xl overflow-hidden border border-gray-200 shadow-sm relative">
      {/* 图例 — 右下角，避免与缩放按钮重叠 */}
      <div className="absolute bottom-3 right-3 z-[600] bg-white/90 backdrop-blur-sm rounded-xl shadow-sm border border-gray-200 px-3 py-2 text-xs space-y-1">
        {dayKeys.map((day) => (
          <div key={day} className="flex items-center gap-2">
            <span
              className="w-3 h-0.5 rounded-full inline-block"
              style={{ backgroundColor: DAY_COLORS[(day - 1) % DAY_COLORS.length] }}
            />
            <span className="text-gray-600">{DAY_LABELS[day - 1] || `第${day}天`}</span>
          </div>
        ))}
      </div>

      <MapContainer
        center={[allPoints[0]?.lat || 35, allPoints[0]?.lng || 139]}
        zoom={12}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBounds points={allPoints} />

        {/* 按天绘制路线 */}
        {dayKeys.map((day) => {
          const points = dayPoints.get(day)!;
          const route: [number, number][] = points.map((p) => [p.lat, p.lng]);
          const color = DAY_COLORS[(day - 1) % DAY_COLORS.length];

          if (route.length < 2) return null;

          return (
            <Polyline
              key={`day-${day}`}
              positions={route}
              color={color}
              weight={3}
              opacity={0.7}
            />
          );
        })}

        {/* 跨日连接线（浅色虚线） */}
        {dayKeys.length > 1 && allPoints.length > 1 && (
          <Polyline
            positions={allPoints.map((p) => [p.lat, p.lng])}
            color="#94a3b8"
            weight={1}
            opacity={0.3}
            dashArray="4 6"
          />
        )}

        {/* 标记点 */}
        {allPoints.map((p, i) => {
          const color = DAY_COLORS[(p.day - 1) % DAY_COLORS.length];
          return (
            <Marker
              key={i}
              position={[p.lat, p.lng]}
              icon={createNumberedIcon(p.index, color)}
            >
              <Popup>
                <div className="text-sm min-w-[160px]">
                  <p className="font-semibold text-gray-800 mb-1">{p.name}</p>
                  <div className="space-y-0.5">
                    <p className="text-xs text-gray-500">
                      📅 {DAY_LABELS[p.day - 1] || `第${p.day}天`} · 第{p.index}站
                    </p>
                    <p className="text-xs text-gray-500">
                      {typeLabels[p.type] || '📍 其他'}
                    </p>
                    <p className="text-xs text-gray-400">
                      {p.lat.toFixed(4)}, {p.lng.toFixed(4)}
                    </p>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
