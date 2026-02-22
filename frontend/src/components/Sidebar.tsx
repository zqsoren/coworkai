import { useState } from "react"
import { Folder, Plus, Bot, Languages, MoreVertical, Pencil, Trash2, Loader2, Users, Crown } from "lucide-react"
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
        createWorkspace
    } = useStore()

    const t = translations[language].sidebar

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
        setIsProcessing(true)
        try {
            await renameWorkspace(renameWorkspaceId, newWorkspaceName)
            setRenameWorkspaceId(null)
            setNewWorkspaceName("")
        } catch (error) {
            console.error(error)
            alert("Rename failed. Check console for details.")
        } finally {
            setIsProcessing(false)
        }
    }

    const handleDeleteWorkspace = async () => {
        if (!deleteWorkspaceId) return
        setIsProcessing(true)
        try {
            await deleteWorkspace(deleteWorkspaceId)
            setDeleteWorkspaceId(null)
        } catch (error) {
            console.error(error)
            alert("Failed to delete workspace. It might be the default one.")
        } finally {
            setIsProcessing(false)
        }
    }

    const handleCreateWorkspace = async () => {
        if (!newWsName.trim()) return
        setIsProcessing(true)
        try {
            await createWorkspace(newWsName)
            setCreateWorkspaceOpen(false)
            setNewWsName("")
        } catch (error) {
            console.error(error)
            alert("Create failed.")
        } finally {
            setIsProcessing(false)
        }
    }

    const handleDeleteAgent = async () => {
        if (!deleteAgentId) return
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
            <div className="p-4 border-b border-gray-300/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="leading-tight">
                        <div className="text-[13px] font-light tracking-wide text-gray-800" style={{ fontFamily: "'Inter', sans-serif" }}>
                            <span className="font-semibold">BASE</span>基石协作
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="text-[11px] text-gray-500 tracking-wider" style={{ fontFamily: "'Inter', sans-serif" }}>coworker.AI</span>
                            <img src="/logo.png" alt="logo" className="w-4 h-3 object-contain" />
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:bg-transparent text-gray-500 hover:text-gray-800"
                        onClick={() => setLanguage(language === 'en' ? 'zh' : 'en')}
                        title="Switch Language"
                    >
                        <Languages className="w-4 h-4" />
                        <span className="sr-only">Switch Language</span>
                    </Button>
                    <SettingsModal />
                </div>
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
                                onClick={() => setCreateWorkspaceOpen(true)}
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
                                            "w-full justify-start px-3 py-2 text-sm overflow-hidden gap-3",
                                            currentAgentId === agent.id
                                                ? "shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-blue-600 font-semibold rounded-xl bg-[#e0e5ec]"
                                                : "hover:shadow-[inset_2px_2px_5px_rgb(163,177,198,0.6),inset_-2px_-2px_5px_rgba(255,255,255,0.5)] text-gray-600 font-normal rounded-xl transition-shadow duration-300 bg-transparent hover:bg-transparent"
                                        )}
                                        onClick={() => setCurrentAgentId(agent.id)}
                                    >
                                        <Bot className={cn("w-4 h-4 shrink-0", currentAgentId === agent.id ? "text-blue-500" : "opacity-50")} />
                                        <span className="truncate">{agent.name}</span>
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

                </div>
            </ScrollArea>

            {/* Dialogs */}

            {/* Create Workspace */}
            <Dialog open={createWorkspaceOpen} onOpenChange={setCreateWorkspaceOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>New Workspace</DialogTitle>
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

        </div>
    )
}
