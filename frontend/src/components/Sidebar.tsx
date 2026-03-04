import { useState, useEffect } from "react"
import { Folder, Plus, Bot, Languages, MoreVertical, Pencil, Trash2, Loader2, Users, Crown, Store, LogOut, LogIn, User } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { useStore } from "@/store"
import { cn } from "@/lib/utils"
import { NewAgentModal } from "./NewAgentModal"
import { NewGroupModal } from "./NewGroupModal"
import { SettingsModal } from "./SettingsModal"
import { translations } from "@/lib/i18n"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function Sidebar() {
    const {
        workspaces,
        currentWorkspaceId,
        agents,
        currentAgentId,
        groups,
        currentGroupId,
        setCurrentWorkspaceId,
        setCurrentAgentId,
        setCurrentGroupId,
        language,
        setLanguage,
        renameWorkspace,
        deleteWorkspace,
        deleteAgent,
        createWorkspace,
        requireAuth,
        activeView,
        setActiveView,
        unreadAgents,
        checkInbox,
        user,
        isAuthenticated,
        logout,
        openLoginModal
    } = useStore()

    const t = translations[language].sidebar

    // Polling for inbox unread messages
    useEffect(() => {
        if (!currentWorkspaceId) return;
        checkInbox();
        const interval = setInterval(checkInbox, 30000); // 30 seconds
        return () => clearInterval(interval);
    }, [currentWorkspaceId, checkInbox]);

    // --- State for Dialogs ---
    const [renameWorkspaceId, setRenameWorkspaceId] = useState<string | null>(null)
    const [newWorkspaceName, setNewWorkspaceName] = useState("")
    const [deleteWorkspaceId, setDeleteWorkspaceId] = useState<string | null>(null)

    const [createWorkspaceOpen, setCreateWorkspaceOpen] = useState(false)
    const [newWsName, setNewWsName] = useState("")

    const [deleteAgentId, setDeleteAgentId] = useState<string | null>(null)

    const [isProcessing, setIsProcessing] = useState(false)

    // --- Handlers ---

    const handleRenameWorkspace = async () => {
        if (!renameWorkspaceId || !newWorkspaceName.trim()) return
        if (!requireAuth()) return
        setIsProcessing(true)
        try {
            await renameWorkspace(renameWorkspaceId, newWorkspaceName)
            setRenameWorkspaceId(null)
            setNewWorkspaceName("")
        } catch (error) {
            console.error(error)
        } finally {
            setIsProcessing(false)
        }
    }

    const handleDeleteWorkspace = async () => {
        if (!deleteWorkspaceId) return
        if (!requireAuth()) return
        setIsProcessing(true)
        try {
            await deleteWorkspace(deleteWorkspaceId)
            setDeleteWorkspaceId(null)
        } catch (error) {
            console.error(error)
        } finally {
            setIsProcessing(false)
        }
    }

    const handleCreateWorkspace = async () => {
        if (!newWsName.trim()) return
        if (!requireAuth()) return
        setIsProcessing(true)
        try {
            await createWorkspace(newWsName)
            setCreateWorkspaceOpen(false)
            setNewWsName("")
        } catch (error) {
            console.error("创建工作区失败:", error)
        } finally {
            setIsProcessing(false)
        }
    }

    const handleDeleteAgent = async () => {
        if (!deleteAgentId) return
        if (!requireAuth()) return
        setIsProcessing(true)
        try {
            await deleteAgent(deleteAgentId)
            setDeleteAgentId(null)
        } catch (error) {
            console.error(error)
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="flex h-full flex-col bg-[#e0e5ec] text-gray-700 overflow-hidden border-none rounded-none shadow-none">
            {/* Header */}
            <div className="px-4 py-5 border-b border-gray-300/50 flex items-center justify-center">
                <img src="/logo.png" alt="BASE基石协作 coworker.AI" className="h-10 object-contain" />
            </div>

            {/* Content */}
            <ScrollArea className="flex-1">
                <div className="p-3 space-y-6">

                    {/* System / Meta Agent */}
                    <div className="px-1">
                        <div className="space-y-1">
                            <Button
                                variant="ghost"
                                className={cn(
                                    "w-full justify-start px-3 py-2.5 text-sm font-bold overflow-hidden mb-4 gap-3 transition-transform hover:translate-y-[-1px]",
                                    "shadow-[3px_3px_6px_rgb(163,177,198,0.6),-3px_-3px_6px_rgba(255,255,255,0.5)] bg-[#e0e5ec] text-amber-600 border border-white/60 rounded-xl"
                                )}
                                onClick={() => {
                                    setCurrentAgentId("meta_agent");
                                }}
                            >
                                <Crown className="w-4 h-4 shrink-0 text-amber-500" />
                                <span className="truncate">超级助手</span>
                            </Button>
                        </div>
                    </div>

                    {/* Workspaces */}
                    <div className="px-1">
                        <h3 className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            {t.workspaces}
                        </h3>
                        <div className="space-y-1">
                            {workspaces.map(ws => (
                                <div key={ws.id} className="group flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start px-3 py-2 text-sm overflow-hidden gap-3",
                                            currentWorkspaceId === ws.id
                                                ? "shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-blue-600 font-semibold rounded-xl bg-[#e0e5ec]"
                                                : "hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-gray-600 font-normal rounded-xl transition-shadow duration-300 bg-transparent hover:bg-transparent"
                                        )}
                                        onClick={() => setCurrentWorkspaceId(ws.id)}
                                    >
                                        <Folder className={cn("w-4 h-4 shrink-0", currentWorkspaceId === ws.id ? "text-blue-500" : "opacity-70")} />
                                        <span className="truncate">{ws.name}</span>
                                    </Button>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-50 hover:bg-transparent transition-opacity">
                                                <MoreVertical className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem onSelect={() => {
                                                setNewWorkspaceName(ws.name)
                                                setRenameWorkspaceId(ws.id)
                                            }}>
                                                <Pencil className="mr-2 h-4 w-4" /> Rename
                                            </DropdownMenuItem>
                                            <DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={() => setDeleteWorkspaceId(ws.id)}>
                                                <Trash2 className="mr-2 h-4 w-4" /> Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            ))}
                            <Button
                                variant="ghost"
                                className="w-full justify-start px-3 py-2 text-sm font-normal text-gray-600 hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] rounded-xl transition-shadow duration-300 mt-1 gap-3 hover:bg-transparent opacity-60 hover:opacity-100"
                                onClick={() => {
                                    if (requireAuth()) {
                                        setCreateWorkspaceOpen(true)
                                    }
                                }}
                            >
                                <Plus className="w-4 h-4 shrink-0" /> <span className="truncate">New Workspace</span>
                            </Button>
                        </div>
                    </div>

                    {/* Agents */}
                    <div className="px-1">
                        <h3 className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            {t.agents}
                        </h3>
                        <div className="space-y-1">
                            {agents.filter(a => a.id !== 'meta_agent').map(agent => (
                                <div key={agent.id} className="group flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start px-3 py-2 text-sm overflow-hidden gap-3 relative",
                                            currentAgentId === agent.id
                                                ? "shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-blue-600 font-semibold rounded-xl bg-[#e0e5ec]"
                                                : "hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-gray-600 font-normal rounded-xl transition-shadow duration-300 bg-transparent hover:bg-transparent"
                                        )}
                                        onClick={() => setCurrentAgentId(agent.id)}
                                    >
                                        <Bot className={cn("w-4 h-4 shrink-0", currentAgentId === agent.id ? "text-blue-500" : "opacity-50")} />
                                        <span className="truncate">{agent.name}</span>
                                        {/* Unread dot indicator */}
                                        {unreadAgents.has(agent.id) && (
                                            <span className="absolute right-3 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-red-500 shadow-[0_0_4px_rgba(239,68,68,0.8)]" />
                                        )}
                                    </Button>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-50 hover:bg-transparent transition-opacity">
                                                <MoreVertical className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={() => setDeleteAgentId(agent.id)}>
                                                <Trash2 className="mr-2 h-4 w-4" /> Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            ))}
                            {/* NewAgentModal needs its trigger to match */}
                            <div className="w-full flex">
                                <NewAgentModal />
                            </div>
                        </div>
                    </div>

                    {/* Group Chats */}
                    <div className="px-1">
                        <h3 className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Group Chats
                        </h3>
                        <div className="space-y-1">
                            {Array.isArray(groups) && groups.map((group: any) => (
                                <div key={group.id} className="group flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            "w-full justify-start px-3 py-2 text-sm overflow-hidden gap-3",
                                            currentGroupId === group.id
                                                ? "shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-blue-600 font-semibold rounded-xl bg-[#e0e5ec]"
                                                : "hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-gray-600 font-normal rounded-xl transition-shadow duration-300 bg-transparent hover:bg-transparent"
                                        )}
                                        onClick={() => setCurrentGroupId(group.id)}
                                    >
                                        <Users className={cn("w-4 h-4 shrink-0", currentGroupId === group.id ? "text-blue-500" : "opacity-50")} />
                                        <span className="truncate">{group.name}</span>
                                    </Button>
                                    {/* TODO: Add Delete Group option */}
                                </div>
                            ))}
                            <div className="w-full flex">
                                <NewGroupModal />
                            </div>
                        </div>
                    </div>

                    {/* Agent Market Entry */}
                    <div className="pt-4 pb-2 border-t mt-4 border-gray-300/50">
                        <Button
                            variant="ghost"
                            className={cn(
                                "w-full justify-start px-3 py-2.5 text-sm font-semibold overflow-hidden gap-3",
                                activeView === 'market'
                                    ? "shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-blue-600 rounded-xl bg-[#e0e5ec]"
                                    : "shadow-[3px_3px_6px_rgb(163,177,198,0.6),-3px_-3px_6px_rgba(255,255,255,0.5)] text-gray-700 rounded-xl transition-shadow duration-300 border border-white/60 bg-[#e0e5ec] hover:translate-y-[-1px]"
                            )}
                            onClick={() => setActiveView('market')}
                        >
                            <Store className={cn("w-4 h-4 shrink-0", activeView === 'market' ? "text-blue-500" : "text-emerald-500")} />
                            <span className="truncate">智能体市场</span>
                            <span className="ml-auto flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        </Button>
                    </div>

                </div>
            </ScrollArea>

            {/* Footer — User Profile & Settings */}
            <div className="px-3 py-3 border-t border-gray-300/50 space-y-2">
                {/* User Profile Row */}
                {isAuthenticated && user ? (
                    <div className="flex items-center gap-2 px-1">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shadow-md shrink-0">
                            {user.username?.charAt(0).toUpperCase() || <User className="w-4 h-4" />}
                        </div>
                        <span className="text-sm font-medium text-gray-700 truncate flex-1">{user.username}</span>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors shrink-0"
                            onClick={logout}
                            title="退出登录"
                        >
                            <LogOut className="w-3.5 h-3.5" />
                        </Button>
                    </div>
                ) : (
                    <Button
                        variant="ghost"
                        className="w-full justify-start px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50/50 rounded-xl gap-2"
                        onClick={openLoginModal}
                    >
                        <LogIn className="w-4 h-4" />
                        登录
                    </Button>
                )}
                {/* Settings Row */}
                <div className="flex items-center justify-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:bg-transparent text-gray-400 hover:text-gray-700"
                        onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
                        title="Switch Language"
                    >
                        <Languages className="w-4 h-4" />
                        <span className="sr-only">Switch Language</span>
                    </Button>
                    <SettingsModal />
                </div>
            </div>

            {/* Dialogs */}

            {/* Create Workspace */}
            <Dialog open={createWorkspaceOpen} onOpenChange={setCreateWorkspaceOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>New Workspace</DialogTitle>
                        <DialogDescription>Create a new workspace to organize your agents.</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="ws-name" className="text-right">Name</Label>
                            <Input id="ws-name" value={newWsName} onChange={(e) => setNewWsName(e.target.value)} className="col-span-3" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={handleCreateWorkspace} disabled={isProcessing}>
                            {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Create
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rename Workspace */}
            <Dialog open={!!renameWorkspaceId} onOpenChange={(open) => !open && setRenameWorkspaceId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Rename Workspace</DialogTitle>
                        <DialogDescription>Enter a new name for this workspace.</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="ws-rename" className="text-right">Name</Label>
                            <Input id="ws-rename" value={newWorkspaceName} onChange={(e) => setNewWorkspaceName(e.target.value)} className="col-span-3" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={handleRenameWorkspace} disabled={isProcessing}>
                            {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Save
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Workspace Confirmation */}
            <Dialog open={!!deleteWorkspaceId} onOpenChange={(open) => !open && setDeleteWorkspaceId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Workspace?</DialogTitle>
                        <DialogDescription>
                            This will permanently delete the workspace and all its agents. this action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteWorkspaceId(null)}>Cancel</Button>
                        <Button variant="destructive" onClick={handleDeleteWorkspace} disabled={isProcessing}>
                            {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>


            {/* Delete Agent Confirmation */}
            <Dialog open={!!deleteAgentId} onOpenChange={(open) => !open && setDeleteAgentId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Delete Agent?</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete this agent? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteAgentId(null)}>Cancel</Button>
                        <Button variant="destructive" onClick={handleDeleteAgent} disabled={isProcessing}>
                            {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

        </div >
    )
}
