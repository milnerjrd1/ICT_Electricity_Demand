import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function Shell() {
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <TopBar />
      <div style={{ display: 'flex', flex: 1, marginTop: '52px', overflow: 'hidden' }}>
        <Sidebar />
        <main
          style={{
            marginLeft: '220px',
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            background: 'var(--bg-base)',
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
