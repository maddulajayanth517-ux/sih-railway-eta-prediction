export default function DashboardPage() {
  return (
    <main style={{
      minHeight: '100vh',
      background: '#020817',
      color: '#e2e8f0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'Arial, sans-serif',
    }}>
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <p style={{ letterSpacing: '0.25rem', textTransform: 'uppercase', color: '#7dd3fc', marginBottom: '1rem' }}>
          Command Center
        </p>
        <h1 style={{ fontSize: '2.5rem', margin: 0 }}>Station Master Dashboard</h1>
        <p style={{ marginTop: '0.75rem', color: '#94a3b8' }}>
          The live rail tracking interface is ready.
        </p>
      </div>
    </main>
  );
}
