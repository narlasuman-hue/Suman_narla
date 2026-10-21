import React, { useState } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const SIDEBAR_KEY = 'sidebar-open';

/** Remembered per browser; storage can be unavailable (private mode), so default to open. */
const loadSidebarOpen = () => {
  try {
    return localStorage.getItem(SIDEBAR_KEY) !== 'false';
  } catch {
    return true;
  }
};

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(loadSidebarOpen);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleSidebar = () => {
    const next = !sidebarOpen;
    setSidebarOpen(next);
    try {
      localStorage.setItem(SIDEBAR_KEY, String(next));
    } catch {
      // Not remembered; it still toggles.
    }
  };

  return (
    <div className="flex h-screen flex-col bg-canvas">
      <Header
        onMenuToggle={toggleSidebar}
        onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
      />

      <div className="flex min-h-0 flex-1">
        <Sidebar
          isOpen={sidebarOpen}
          isMobileOpen={mobileMenuOpen}
          onToggle={toggleSidebar}
          onMobileClose={() => setMobileMenuOpen(false)}
        />
        <main className="min-w-0 flex-1 overflow-auto">
          <div className="mx-auto max-w-[1600px] p-4 sm:p-6">{children}</div>
        </main>
      </div>

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

export default Layout;
