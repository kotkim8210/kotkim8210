"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type RevenuePoint = { date: string; revenue: number; clicks: number };
type Variant = { name: "A" | "B"; visitors: number; conversions: number };

const revenueData: RevenuePoint[] = [
  { date: "2025-04-01", revenue: 412_000, clicks: 1820 },
  { date: "2025-04-02", revenue: 398_500, clicks: 1755 },
  { date: "2025-04-03", revenue: 441_200, clicks: 1902 },
  { date: "2025-04-04", revenue: 467_800, clicks: 1988 },
  { date: "2025-04-05", revenue: 523_400, clicks: 2180 },
  { date: "2025-04-06", revenue: 550_100, clicks: 2265 },
  { date: "2025-04-07", revenue: 488_600, clicks: 2041 },
  { date: "2025-04-08", revenue: 515_900, clicks: 2144 },
  { date: "2025-04-09", revenue: 559_300, clicks: 2308 },
  { date: "2025-04-10", revenue: 602_700, clicks: 2472 },
  { date: "2025-04-11", revenue: 634_800, clicks: 2585 },
  { date: "2025-04-12", revenue: 689_200, clicks: 2744 },
  { date: "2025-04-13", revenue: 712_500, clicks: 2812 },
  { date: "2025-04-14", revenue: 695_100, clicks: 2756 },
];

const variants: [Variant, Variant] = [
  { name: "A", visitors: 4821, conversions: 231 },
  { name: "B", visitors: 4795, conversions: 288 },
];

function formatKRW(n: number) {
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency: "KRW",
    maximumFractionDigits: 0,
  }).format(n);
}

function rate(v: Variant) {
  return v.conversions / v.visitors;
}

function zTest(a: Variant, b: Variant) {
  const pA = rate(a);
  const pB = rate(b);
  const pPool = (a.conversions + b.conversions) / (a.visitors + b.visitors);
  const se = Math.sqrt(pPool * (1 - pPool) * (1 / a.visitors + 1 / b.visitors));
  const z = se === 0 ? 0 : (pB - pA) / se;
  const pTwoSided = 2 * (1 - normalCdf(Math.abs(z)));
  const lift = pA === 0 ? 0 : (pB - pA) / pA;
  return { z, pTwoSided, lift };
}

function normalCdf(x: number) {
  const b1 = 0.319381530;
  const b2 = -0.356563782;
  const b3 = 1.781477937;
  const b4 = -1.821255978;
  const b5 = 1.330274429;
  const p = 0.2316419;
  const t = 1 / (1 + p * x);
  const poly = ((((b5 * t + b4) * t + b3) * t + b2) * t + b1) * t;
  const pdf = Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
  return 1 - pdf * poly;
}

export default function Page() {
  const totalRevenue = revenueData.reduce((s, p) => s + p.revenue, 0);
  const totalClicks = revenueData.reduce((s, p) => s + p.clicks, 0);
  const avgDailyRevenue = Math.round(totalRevenue / revenueData.length);

  const [a, b] = variants;
  const { z, pTwoSided, lift } = zTest(a, b);
  const significant = pTwoSided < 0.05;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10 space-y-10">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-widest text-zinc-500">
          Coupang Partners · MVP
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          매출 추이 대시보드
        </h1>
        <p className="text-sm text-zinc-500">
          모의 데이터 기반 · 최근 14일 / A·B 테스트 비교
        </p>
      </header>

      <section
        aria-label="요약 지표"
        className="grid grid-cols-1 gap-4 sm:grid-cols-3"
      >
        <KpiCard label="총 매출 (14일)" value={formatKRW(totalRevenue)} />
        <KpiCard
          label="총 클릭수"
          value={totalClicks.toLocaleString("ko-KR")}
        />
        <KpiCard label="일 평균 매출" value={formatKRW(avgDailyRevenue)} />
      </section>

      <section
        aria-labelledby="revenue-chart-heading"
        className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
      >
        <h2
          id="revenue-chart-heading"
          className="text-lg font-medium tracking-tight"
        >
          일별 매출 추이
        </h2>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={revenueData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3f3f46" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#3f3f46" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(d) => d.slice(5)}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `${Math.round(v / 1000)}k`}
              />
              <Tooltip
                formatter={(v: number) => formatKRW(v)}
                labelFormatter={(l) => `${l}`}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#18181b"
                strokeWidth={2}
                fill="url(#revGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section
        aria-labelledby="ab-heading"
        className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
      >
        <h2 id="ab-heading" className="text-lg font-medium tracking-tight">
          A/B 테스트 비교
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          2-proportion z-test · α = 0.05 (양측)
        </p>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <VariantCard variant={a} />
          <VariantCard variant={b} highlight={significant} />
        </div>
        <dl className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
          <Metric label="B 리프트" value={`${(lift * 100).toFixed(2)}%`} />
          <Metric label="z" value={z.toFixed(3)} />
          <Metric label="p (two-sided)" value={pTwoSided.toFixed(4)} />
          <Metric
            label="결과"
            value={significant ? "유의함 (B 우세)" : "유의하지 않음"}
          />
        </dl>
      </section>

      <footer className="text-xs text-zinc-400">
        Built with Next.js 15 + Recharts · everything-claude-code 플러그인 워크플로우 테스트용 MVP.
      </footer>
    </main>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function VariantCard({
  variant,
  highlight = false,
}: {
  variant: Variant;
  highlight?: boolean;
}) {
  const cr = (rate(variant) * 100).toFixed(2);
  return (
    <div
      className={`rounded-xl border p-5 ${
        highlight
          ? "border-emerald-400 bg-emerald-50"
          : "border-zinc-200 bg-zinc-50"
      }`}
    >
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">변형 {variant.name}</p>
        <p className="text-xs text-zinc-500">
          방문 {variant.visitors.toLocaleString("ko-KR")} / 전환{" "}
          {variant.conversions.toLocaleString("ko-KR")}
        </p>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{cr}%</p>
      <p className="text-xs text-zinc-500">전환율</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-zinc-500">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}
