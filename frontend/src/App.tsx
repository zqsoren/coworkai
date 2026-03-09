import { useEffect, useState } from "react"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { useStore } from "@/store"
import { Sidebar } from "@/components/Sidebar"
import { RightPanel } from "@/components/RightPanel"
import { Chat } from "@/components/Chat"
import { Basket } from "@/components/Basket"
import LoginModal from "@/components/LoginModal"
import { AgentMarket } from "@/components/AgentMarket"
import { useIsTablet } from "@/hooks/useMediaQuery"
import { Menu, PanelRight, X } from "lucide-react"

export default function App() {
  const {
    currentWorkspaceId,
    currentAgentId,
    currentGroupId,
    loadWorkspaces,
    loadAgents,
    isAuthenticated,
    initAuth,
    openLoginModal,
    logout,
    activeView,
  } = useStore()

  const isTablet = useIsTablet()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [rightPanelOpen, setRightPanelOpen] = useState(false)

  // Close drawers when switching back to desktop
  useEffect(() => {
    if (!isTablet) {
      setSidebarOpen(false)
      setRightPanelOpen(false)
    }
  }, [isTablet])

  // Close sidebar when selecting an agent/group (on tablet)
  useEffect(() => {
    if (isTablet) setSidebarOpen(false)
  }, [currentAgentId, currentGroupId])

  // Restore auth from localStorage on first load
  useEffect(() => {
    initAuth()
    const handler = () => {
      logout()
      openLoginModal()
    }
    window.addEventListener('auth_show_login', handler)
    return () => window.removeEventListener('auth_show_login', handler)
  }, [])

  // Load workspaces when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadWorkspaces()
    }
  }, [isAuthenticated])

  // Load Agents when Workspace Changes
  useEffect(() => {
    if (currentWorkspaceId) {
      loadAgents(currentWorkspaceId)
    }
  }, [currentWorkspaceId])

  // ---- TABLET LAYOUT (≤1024px) ----
  if (isTablet) {
    return (
      <div className="h-screen w-full bg-background text-foreground overflow-hidden flex flex-col font-sans relative">
        {/* Top Bar */}
        <div className="h-12 border-b flex items-center justify-between px-3 bg-[#e0e5ec] shrink-0 z-30">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-black/5 active:bg-black/10 transition-colors"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
          <img src="/logo.png" alt="BASE基石协作" className="h-7 object-contain" />
          <button
            onClick={() => setRightPanelOpen(true)}
            className="p-2 rounded-lg hover:bg-black/5 active:bg-black/10 transition-colors"
          >
            <PanelRight className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {activeView === 'market' ? <AgentMarket /> : <Chat />}
        </div>

        {/* Sidebar Drawer Overlay */}
        {sidebarOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/30 z-40 animate-in fade-in duration-200"
              onClick={() => setSidebarOpen(false)}
            />
            <div className="fixed inset-y-0 left-0 w-[280px] z-50 bg-[#e0e5ec] shadow-2xl animate-in slide-in-from-left duration-300">
              <div className="absolute top-3 right-3 z-10">
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1.5 rounded-full hover:bg-black/5 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <Sidebar />
            </div>
          </>
        )}

        {/* Right Panel Drawer Overlay */}
        {rightPanelOpen && (
          <>
            <div
              className="fixed inset-0 bg-black/30 z-40 animate-in fade-in duration-200"
              onClick={() => setRightPanelOpen(false)}
            />
            <div className="fixed inset-y-0 right-0 w-[320px] z-50 bg-white shadow-2xl animate-in slide-in-from-right duration-300">
              <div className="absolute top-3 left-3 z-10">
                <button
                  onClick={() => setRightPanelOpen(false)}
                  className="p-1.5 rounded-full hover:bg-black/5 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <RightPanel />
            </div>
          </>
        )}

        <Basket />
        <LoginModal />
      </div>
    )
  }

  // ---- DESKTOP LAYOUT (>1024px) — unchanged ----
  return (
    <div className="h-screen w-full bg-background text-foreground overflow-hidden flex flex-col font-sans">
      <ResizablePanelGroup direction="horizontal">

        {/* LEFT SIDEBAR (Workspaces & Agents) */}
        <ResizablePanel defaultSize={20} minSize={15} maxSize={30} className="bg-muted/10 border-r">
          <Sidebar />
        </ResizablePanel>

        <ResizableHandle />

        {activeView === 'market' ? (
          <ResizablePanel defaultSize={80}>
            <AgentMarket />
          </ResizablePanel>
        ) : (
          <>
            {/* MIDDLE CHAT (Main Area) */}
            <ResizablePanel defaultSize={60}>
              <Chat />
            </ResizablePanel>

            <ResizableHandle />

            {/* RIGHT CONTEXT PANEL */}
            <ResizablePanel defaultSize={20} minSize={15} maxSize={30} className="bg-muted/10 border-l">
              <RightPanel />
            </ResizablePanel>
          </>
        )}

      </ResizablePanelGroup>
      {/* Floating Basket - always on top, accessible from any panel */}
      <Basket />
      {/* Login Modal - floats on top when triggered */}
      <LoginModal />
    </div>
  )
}
