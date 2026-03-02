import { useEffect } from "react"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { useStore } from "@/store"
import { Sidebar } from "@/components/Sidebar"
import { RightPanel } from "@/components/RightPanel"
import { Chat } from "@/components/Chat"
import { Basket } from "@/components/Basket"
import LoginModal from "@/components/LoginModal"
import { AgentMarket } from "@/components/AgentMarket"

export default function App() {
  const {
    currentWorkspaceId,
    loadWorkspaces,
    loadAgents,
    isAuthenticated,
    initAuth,
    openLoginModal,
    logout,
    activeView,
  } = useStore()

  // Restore auth from localStorage on first load
  useEffect(() => {
    initAuth()

    // Listen for 401 responses — show login modal and clear auth state
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

  // Always show main app, login modal floats on top when needed
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
