export default function PrivacyPolicyPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-black tracking-tight text-[var(--hp-text)]">Privacy Policy</h1>
      <p className="mt-2 text-sm text-[var(--hp-text-muted)]">Effective date: July 1, 2021</p>
      <article className="prose prose-sm mt-8 max-w-none text-[var(--hp-text)] dark:prose-invert">
        <p>
          Your privacy is important to us. We collect and process information only when needed to
          provide and improve our services.
        </p>
        <p>
          We retain data only for as long as necessary and protect it using commercially acceptable
          safeguards against unauthorized access, disclosure, and misuse.
        </p>
        <p>
          We do not publicly share personally identifying information except when required by law.
          External links may follow different privacy practices.
        </p>
        <p>
          By continuing to use this site, you accept these practices. Contact support if you have
          questions about how we handle your data.
        </p>
      </article>
    </main>
  );
}
