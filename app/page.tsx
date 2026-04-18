const features = [
  {
    title: "App Router",
    desc: "Next.js 15 의 최신 라우팅 규약. 서버 컴포넌트 기본.",
  },
  {
    title: "Tailwind CSS v4",
    desc: "PostCSS 기반의 Zero-config 스타일링.",
  },
  {
    title: "TypeScript Strict",
    desc: "경로 alias(@/*)와 엄격한 타입 체크 활성화.",
  },
];

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.12),transparent_60%)]"
      />
      <div className="relative mx-auto flex max-w-5xl flex-col gap-16 px-6 py-24">
        <header className="flex flex-col items-start gap-4">
          <span className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white/70 px-3 py-1 text-xs font-medium text-neutral-700 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/70 dark:text-neutral-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Scaffold Ready
          </span>
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            kotkim8210
          </h1>
          <p className="max-w-2xl text-lg text-neutral-600 dark:text-neutral-400">
            Next.js 15 · Tailwind CSS v4 · TypeScript 로 구성된 최소 스캐폴드.
            <br />
            <code className="mt-2 inline-block rounded bg-neutral-100 px-2 py-0.5 text-sm dark:bg-neutral-800">
              app/page.tsx
            </code>
            {" 를 수정해 시작하세요."}
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href="https://nextjs.org/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
            >
              Next.js 문서
            </a>
            <a
              href="https://tailwindcss.com/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-neutral-300 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
            >
              Tailwind 문서
            </a>
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-neutral-200 bg-white/70 p-6 backdrop-blur transition hover:border-neutral-300 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-900/60 dark:hover:border-neutral-700"
            >
              <h2 className="text-lg font-semibold">{f.title}</h2>
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                {f.desc}
              </p>
            </div>
          ))}
        </section>

        <footer className="border-t border-neutral-200 pt-8 text-sm text-neutral-500 dark:border-neutral-800">
          Built with Next.js App Router.
        </footer>
      </div>
    </main>
  );
}
