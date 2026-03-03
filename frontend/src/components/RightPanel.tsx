
import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Database, Upload, Loader2, Bell, RefreshCw, Folder, FolderPlus, Zap, Save } from "lucide-react"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { FileTree } from "./FileTree"
import { fetchFileTree, setFileLock, createDirectory, deleteFileItem, renameFileItem, uploadWorkspaceFiles } from "@/lib/api"
import type { FileNode, OutputMode } from "@/lib/api"

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"

// Components
import { KnowledgeBaseModal } from "./KnowledgeBaseModal"
import { PendingChangesList } from "./PendingChangesList"
import { GroupPanel } from "./GroupPanel"
import { AgentSkillsModal } from "./AgentSkillsModal"

// Robot Avatar Options
const AVATAR_OPTIONS = [
    { id: "robot-1", emoji: "🤖" },
    { id: "robot-2", emoji: "🧠" },
    { id: "robot-3", emoji: "⚡" },
    { id: "robot-4", emoji: "🔮" },
    { id: "robot-5", emoji: "🎯" },
    { id: "robot-6", emoji: "🛠️" },
    { id: "robot-7", emoji: "📊" },
    { id: "robot-8", emoji: "🔍" },
    { id: "robot-9", emoji: "💡" },
    { id: "robot-10", emoji: "🚀" },
    { id: "robot-11", emoji: "🎨" },
    { id: "robot-12", emoji: "📝" },
]

export function RightPanel() {
    const { currentWorkspaceId, currentAgentId, currentGroupId, language, pendingChanges, agents, updateAgent } = useStore()
    const t = translations[language].rightPanel

    // File Trees
    const [sharedTree, setSharedTree] = useState<FileNode[]>([])
    const [privateTree, setPrivateTree] = useState<FileNode[]>([])
    const [archivesTree, setArchivesTree] = useState<FileNode[]>([])

    const [isUploading, setIsUploading] = useState(false)
    const [isLoadingFiles, setIsLoadingFiles] = useState(false)
    const [openAgentSkills, setOpenAgentSkills] = useState(false)
    const [openKBManager, setOpenKBManager] = useState(false)

    // New Folder Dialog
    const [isNewFolderOpen, setIsNewFolderOpen] = useState(false)
    const [newFolderParent, setNewFolderParent] = useState("")
    const [newFolderName, setNewFolderName] = useState("")

    // Rename Dialog
    const [isRenameOpen, setIsRenameOpen] = useState(false)
    const [renameTarget, setRenameTarget] = useState<FileNode | null>(null)
    const [renameNewName, setRenameNewName] = useState("")

    // Inline Agent Settings State
    const [agentName, setAgentName] = useState("")
    const [agentPrompt, setAgentPrompt] = useState("")
    const [agentModel, setAgentModel] = useState("")
    const [agentProviderId, setAgentProviderId] = useState("")
    const [agentPersonaMode, setAgentPersonaMode] = useState("normal")
    const [agentAvatar, setAgentAvatar] = useState("robot-1")
    const [showAvatarPicker, setShowAvatarPicker] = useState(false)
    const [providers, setProviders] = useState<any[]>([])
    const [outputModes, setOutputModes] = useState<OutputMode[]>([])
    const [isSaving, setIsSaving] = useState(false)
    const [saveMessage, setSaveMessage] = useState<string | null>(null)

    const agent = agents.find(a => a.id === currentAgentId)

    // Load agent settings when agent changes
    useEffect(() => {
        if (agent) {
            setAgentName(agent.name || "")
            setAgentPrompt(agent.system_prompt || "")
            setAgentProviderId(agent.provider_id || "")
            setAgentModel(agent.model_name || "")
            setAgentPersonaMode(agent.persona_mode || "normal")
            setAgentAvatar((agent as any).avatar || "robot-1")
        }
    }, [currentAgentId, agent?.name, agent?.system_prompt, agent?.provider_id, agent?.model_name])

    // Load providers + output modes
    useEffect(() => {
        const load = async () => {
            try {
                const { fetchProviders: apiFetch, fetchOutputModes } = await import("@/lib/api")
                const [provData, modeData] = await Promise.all([apiFetch(), fetchOutputModes()])
                setProviders(provData)
                setOutputModes(modeData)
            } catch (e) { console.error(e) }
        }
        if (currentAgentId) load()
    }, [currentAgentId])

    // Auto-sync model from provider
    useEffect(() => {
        const selectedProvider = providers.find(p => p.id === agentProviderId)
        if (selectedProvider && (!agentModel || (agent && agent.provider_id !== agentProviderId))) {
            setAgentModel(selectedProvider.models?.[0] || "")
        }
    }, [agentProviderId, providers])

    const handleSaveSettings = async () => {
        if (!currentAgentId) return
        setIsSaving(true)
        try {
            await updateAgent(currentAgentId, {
                name: agentName,
                system_prompt: agentPrompt,
                provider_id: agentProviderId || undefined,
                model_name: agentModel || undefined,
                persona_mode: agentPersonaMode,
                avatar: agentAvatar,
            } as any)
            setSaveMessage("保存成功")
            setTimeout(() => setSaveMessage(null), 2000)
        } catch (error) {
            console.error('Agent 更新失败:', error)
            setSaveMessage("保存失败")
            setTimeout(() => setSaveMessage(null), 2000)
        } finally {
            setIsSaving(false)
        }
    }

    // Corrected refresh with 3 items
    const refreshAll = async () => {
        if (!currentWorkspaceId) return
        setIsLoadingFiles(true)
        try {
            const p1 = fetchFileTree(currentWorkspaceId, undefined, 'shared')
            const p2 = currentAgentId ? fetchFileTree(currentWorkspaceId, currentAgentId, 'private') : Promise.resolve([])
            const p3 = currentAgentId ? fetchFileTree(currentWorkspaceId, currentAgentId, 'archives') : Promise.resolve([])

            const [shared, priv, arch] = await Promise.all([p1, p2, p3])

            setSharedTree(shared)
            setPrivateTree(priv.filter(n => !['archives', 'knowledge_base', 'vector_store', '_metadata.json', 'context'].includes(n.name)))
            setArchivesTree(arch)

        } catch (e) { console.error(e) }
        finally { setIsLoadingFiles(false) }
    }


    useEffect(() => {
        refreshAll()
    }, [currentWorkspaceId, currentAgentId])

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: string) => {
        if (!e.target.files?.length || !currentWorkspaceId || !currentAgentId) return
        setIsUploading(true)
        try {
            let targetPath = `${currentWorkspaceId}/shared`
            if (type === "private") targetPath = `${currentWorkspaceId}/${currentAgentId}`
            if (type === "archives") targetPath = `${currentWorkspaceId}/${currentAgentId}/archives`

            await uploadWorkspaceFiles(targetPath, Array.from(e.target.files))
            await refreshAll()
        } catch (err) {
            console.error(err)
        } finally {
            setIsUploading(false)
        }
    }

    const handleDelete = async (path: string) => {
        if (!confirm(`Delete ${path}? This cannot be undone.`)) return
        await deleteFileItem(path)
        refreshAll()
    }

    // Rename Logic
    const handleRenameStart = (node: FileNode) => {
        setRenameTarget(node)
        setRenameNewName(node.name)
        setIsRenameOpen(true)
    }

    const submitRename = async () => {
        if (!renameTarget || !renameNewName || renameNewName === renameTarget.name) {
            setIsRenameOpen(false)
            return
        }
        const pathParts = renameTarget.path.split('/')
        pathParts.pop()
        const newPath = pathParts.length > 0
            ? [...pathParts, renameNewName].join('/')
            : renameNewName

        try {
            await renameFileItem(renameTarget.path, newPath)
            refreshAll()
        } catch (e) {
            console.error(e)
            alert("Rename failed")
        } finally {
            setIsRenameOpen(false)
        }
    }


    const handleToggleLock = async (path: string, currentLocked: boolean) => {
        await setFileLock(path, !currentLocked)
        refreshAll()
    }

    const handleCreateFolderStart = (parentPath: string) => {
        setNewFolderParent(parentPath)
        setNewFolderName("")
        setIsNewFolderOpen(true)
    }

    const submitCreateFolder = async () => {
        if (!newFolderName) return
        const fullPath = newFolderParent ? `${newFolderParent}/${newFolderName}` : newFolderName
        await createDirectory(fullPath)
        setIsNewFolderOpen(false)
        refreshAll()
    }

    // Drag and Drop Move Handler
    const handleMoveFile = async (sourcePath: string, targetFolder: string) => {
        const fileName = sourcePath.split('/').pop()
        if (!fileName) return

        const newPath = targetFolder ? `${targetFolder}/${fileName}` : fileName

        if (newPath === sourcePath) return

        try {
            await renameFileItem(sourcePath, newPath)
            refreshAll()
        } catch (e) {
            console.error("Move failed", e)
            alert("Move failed")
        }
    }

    // Group mode
    if (currentGroupId) {
        return (
            <div className="h-full flex flex-col">
                <GroupPanel />
            </div>
        )
    }

    if (!currentWorkspaceId || !currentAgentId) {
        return (
            <div className="flex h-full items-center justify-center text-muted-foreground p-4 text-center">
                {translations[language].chat.selectAgent}
            </div>
        )
    }

    const currentAvatar = AVATAR_OPTIONS.find(a => a.id === agentAvatar) || AVATAR_OPTIONS[0]

    return (
        <div className="h-full bg-muted/10 border-l flex flex-col relative">

            {/* Modals */}
            <AgentSkillsModal open={openAgentSkills} onOpenChange={setOpenAgentSkills} />
            <KnowledgeBaseModal open={openKBManager} onOpenChange={setOpenKBManager} />

            {/* New Folder Dialog */}
            <Dialog open={isNewFolderOpen} onOpenChange={setIsNewFolderOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create New Folder</DialogTitle>
                        <DialogDescription>
                            Creating folder in: <code className="bg-muted px-1 rounded">{newFolderParent}</code>
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="name" className="text-right">Name</Label>
                            <Input id="name" value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} className="col-span-3" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={submitCreateFolder}>Create</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Rename Dialog */}
            <Dialog open={isRenameOpen} onOpenChange={setIsRenameOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Rename Item</DialogTitle>
                        <DialogDescription>
                            Enter a new name for: <code className="bg-muted px-1 rounded">{renameTarget?.name}</code>
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="rename-name" className="text-right">Name</Label>
                            <Input id="rename-name" value={renameNewName} onChange={(e) => setRenameNewName(e.target.value)} className="col-span-3" />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={submitRename}>Rename</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Tabs defaultValue="files" className="flex flex-col h-full">
                <div className="px-4 py-3 border-b bg-background/50">
                    <TabsList className="w-full grid grid-cols-2">
                        <TabsTrigger value="files">
                            {t.files}
                            {pendingChanges.length > 0 && (
                                <span className="ml-1.5 w-2 h-2 bg-red-500 rounded-full animate-pulse inline-block" />
                            )}
                        </TabsTrigger>
                        <TabsTrigger value="settings">
                            {t.actions}
                        </TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex-1 overflow-hidden relative">

                    {/* FILES TAB */}
                    <TabsContent value="files" className="absolute inset-0 m-0 flex flex-col overflow-auto">

                        <div className="flex justify-between items-center px-4 py-2 text-xs text-muted-foreground bg-muted/20">
                            <span>File System V2</span>
                            <div className="flex items-center gap-1">
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={refreshAll} disabled={isLoadingFiles} title="Refresh Files">
                                    <RefreshCw className={`w-3 h-3 ${isLoadingFiles ? 'animate-spin' : ''}`} />
                                </Button>
                            </div>
                        </div>

                        <ScrollArea className="flex-1 px-4 pb-10">
                            <div className="space-y-6 mt-4">

                                {/* Shared Workspace Section */}
                                <div>
                                    <div className="flex items-center justify-between mb-2 group">
                                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                            <Folder className="w-4 h-4 text-blue-500" />
                                            {t.sharedFiles || "Shared Files"}
                                        </h3>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleCreateFolderStart(`${currentWorkspaceId}/shared`)} title="New Folder">
                                                <FolderPlus className="w-4 h-4 text-muted-foreground" />
                                            </Button>
                                            <div className="relative">
                                                <Input type="file" multiple className="hidden" id="upload-shared-btn" onChange={(e) => handleUpload(e, "shared")} disabled={isUploading} />
                                                <label htmlFor="upload-shared-btn">
                                                    <div className={cn("h-6 w-6 flex items-center justify-center rounded-md hover:bg-accent cursor-pointer", isUploading && "opacity-50 cursor-not-allowed")}>
                                                        {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4 text-muted-foreground" />}
                                                    </div>
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="pl-2 border-l-2 border-muted/50 ml-1">
                                        <FileTree
                                            nodes={sharedTree}
                                            rootPath={`${currentWorkspaceId}/shared`}
                                            onSelect={() => { }}
                                            onToggleLock={handleToggleLock}
                                            onCreateFolder={handleCreateFolderStart}
                                            onRename={handleRenameStart}
                                            onDelete={handleDelete}
                                            onMove={handleMoveFile}
                                        />
                                        {sharedTree.length === 0 && (
                                            <div className="text-xs text-muted-foreground py-2 italic">No files</div>
                                        )}
                                    </div>
                                </div>

                                {/* Agent Private Section */}
                                <div>
                                    <div className="flex items-center justify-between mb-2 group">
                                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                            <Folder className="w-4 h-4 text-orange-500" />
                                            {t.privateFiles || "Private Files"}
                                        </h3>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleCreateFolderStart(`${currentWorkspaceId}/${currentAgentId}`)} title="New Folder">
                                                <FolderPlus className="w-4 h-4 text-muted-foreground" />
                                            </Button>
                                            <div className="relative">
                                                <Input type="file" multiple className="hidden" id="upload-private-btn" onChange={(e) => handleUpload(e, "private")} disabled={isUploading} />
                                                <label htmlFor="upload-private-btn">
                                                    <div className={cn("h-6 w-6 flex items-center justify-center rounded-md hover:bg-accent cursor-pointer", isUploading && "opacity-50 cursor-not-allowed")}>
                                                        {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4 text-muted-foreground" />}
                                                    </div>
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="pl-2 border-l-2 border-muted/50 ml-1">
                                        <FileTree
                                            nodes={privateTree}
                                            rootPath={`${currentWorkspaceId}/${currentAgentId}`}
                                            onSelect={() => { }}
                                            onToggleLock={handleToggleLock}
                                            onCreateFolder={handleCreateFolderStart}
                                            onRename={handleRenameStart}
                                            onDelete={handleDelete}
                                            onMove={handleMoveFile}
                                        />
                                        {privateTree.length === 0 && (
                                            <div className="text-xs text-muted-foreground py-2 italic">No files</div>
                                        )}
                                    </div>
                                </div>

                                {/* Archives Section */}
                                <div>
                                    <div className="flex items-center justify-between mb-2 group">
                                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                            <Folder className="w-4 h-4 text-gray-500" />
                                            {t.archives || "Archives"}
                                        </h3>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleCreateFolderStart(`${currentWorkspaceId}/${currentAgentId}/archives`)} title="New Folder">
                                                <FolderPlus className="w-4 h-4 text-muted-foreground" />
                                            </Button>
                                            <div className="relative">
                                                <Input type="file" multiple className="hidden" id="upload-archives-btn" onChange={(e) => handleUpload(e, "archives")} disabled={isUploading} />
                                                <label htmlFor="upload-archives-btn">
                                                    <div className={cn("h-6 w-6 flex items-center justify-center rounded-md hover:bg-accent cursor-pointer", isUploading && "opacity-50 cursor-not-allowed")}>
                                                        {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4 text-muted-foreground" />}
                                                    </div>
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="pl-2 border-l-2 border-muted/50 ml-1">
                                        <FileTree
                                            nodes={archivesTree}
                                            rootPath={`${currentWorkspaceId}/${currentAgentId}/archives`}
                                            onSelect={() => { }}
                                            onToggleLock={handleToggleLock}
                                            onCreateFolder={handleCreateFolderStart}
                                            onRename={handleRenameStart}
                                            onDelete={handleDelete}
                                            onMove={handleMoveFile}
                                        />
                                        {archivesTree.length === 0 && (
                                            <div className="text-xs text-muted-foreground py-2 italic">No files</div>
                                        )}
                                    </div>
                                </div>

                            </div>
                        </ScrollArea>

                        {/* Pending Changes at bottom of Files tab */}
                        {pendingChanges.length > 0 && (
                            <div className="border-t">
                                <div className="p-3 flex items-center gap-2 font-semibold text-sm bg-muted/40">
                                    <Bell className="w-4 h-4 text-orange-500" />
                                    {t.pendingChanges}
                                </div>
                                <PendingChangesList />
                            </div>
                        )}
                    </TabsContent>

                    {/* AGENT SETTINGS TAB */}
                    <TabsContent value="settings" className="absolute inset-0 m-0 flex flex-col overflow-auto bg-white dark:bg-zinc-950 font-sans">
                        <ScrollArea className="flex-1">
                            <div className="p-5 space-y-6">

                                {/* Avatar + Name Header */}
                                <div className="flex items-center gap-4 pb-4 border-b border-gray-200 dark:border-zinc-800">
                                    <div className="relative">
                                        <button
                                            onClick={() => setShowAvatarPicker(!showAvatarPicker)}
                                            className="w-12 h-12 rounded-none bg-transparent flex items-center justify-center text-2xl hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors cursor-pointer border border-gray-300 dark:border-zinc-700"
                                            title="点击更换头像"
                                        >
                                            {currentAvatar.emoji}
                                        </button>
                                        {/* Avatar Picker Dropdown */}
                                        {showAvatarPicker && (
                                            <div className="absolute top-14 left-0 z-50 bg-white dark:bg-zinc-950 border border-gray-300 dark:border-zinc-800 p-3 w-[210px] shadow-sm">
                                                <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2 font-semibold">更换头像 / AVATAR</div>
                                                <div className="grid grid-cols-4 gap-2">
                                                    {AVATAR_OPTIONS.map(opt => (
                                                        <button
                                                            key={opt.id}
                                                            onClick={() => {
                                                                setAgentAvatar(opt.id)
                                                                setShowAvatarPicker(false)
                                                            }}
                                                            className={cn(
                                                                "w-10 h-10 rounded-none flex items-center justify-center text-lg hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer border border-transparent",
                                                                agentAvatar === opt.id && "border-black dark:border-white bg-gray-50 dark:bg-zinc-900"
                                                            )}
                                                        >
                                                            {opt.emoji}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <Input
                                            value={agentName}
                                            onChange={(e) => setAgentName(e.target.value)}
                                            className="text-lg font-semibold border-none shadow-none p-0 h-auto focus-visible:ring-0 bg-transparent rounded-none"
                                            placeholder="Agent 名称"
                                        />
                                        <div className="text-[10px] uppercase tracking-wider text-gray-400 mt-1 flex items-center gap-2">
                                            ID: AGT-{currentAgentId.substring(0, 4).toUpperCase()}
                                        </div>
                                    </div>
                                </div>

                                {/* Settings Section */}
                                <div className="space-y-5">
                                    {/* System Prompt */}
                                    <div className="space-y-2">
                                        <Label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">系统提示词</Label>
                                        <Textarea
                                            value={agentPrompt}
                                            onChange={(e) => setAgentPrompt(e.target.value)}
                                            className="min-h-[120px] text-sm resize-y rounded-none border-gray-300 dark:border-zinc-700 bg-transparent focus-visible:ring-0 focus-visible:border-black dark:focus-visible:border-white shadow-none"
                                            placeholder="输入系统提示词..."
                                        />
                                        <div className="flex justify-end pt-1">
                                            <div className="flex items-center gap-2">
                                                {saveMessage && (
                                                    <span className={cn("text-[10px] font-medium", saveMessage.includes("成功") ? "text-green-600" : "text-red-500")}>
                                                        {saveMessage}
                                                    </span>
                                                )}
                                                <Button
                                                    onClick={handleSaveSettings}
                                                    disabled={isSaving}
                                                    className="h-7 px-3 w-auto rounded-none border border-black dark:border-white bg-white dark:bg-black text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black uppercase tracking-widest text-[10px] font-bold transition-colors shadow-none"
                                                >
                                                    {isSaving ? (
                                                        <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                                                    ) : (
                                                        <Save className="mr-1.5 h-3 w-3" />
                                                    )}
                                                    {isSaving ? "SAVING..." : "SAVE.PROMPT"}
                                                </Button>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Provider */}
                                    <div className="space-y-2">
                                        <Label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">模型提供商</Label>
                                        <Select
                                            value={agentProviderId}
                                            onValueChange={async (val) => {
                                                setAgentProviderId(val)
                                                if (currentAgentId) {
                                                    try { await updateAgent(currentAgentId, { provider_id: val } as any) } catch (e) { console.error(e) }
                                                }
                                            }}
                                        >
                                            <SelectTrigger className="text-sm rounded-none border-gray-300 dark:border-zinc-700 bg-transparent focus:ring-0 focus:border-black dark:focus:border-white shadow-none">
                                                <SelectValue placeholder="选择提供商" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-none border-gray-300 dark:border-zinc-800">
                                                {providers.map(p => (
                                                    <SelectItem key={p.id} value={p.id} className="rounded-none cursor-pointer">{p.name} ({p.type})</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Output Mode */}
                                    <div className="space-y-2">
                                        <Label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">输出模式</Label>
                                        <Select
                                            value={agentPersonaMode}
                                            onValueChange={async (val) => {
                                                setAgentPersonaMode(val)
                                                if (currentAgentId) {
                                                    try { await updateAgent(currentAgentId, { persona_mode: val } as any) } catch (e) { console.error(e) }
                                                }
                                            }}
                                        >
                                            <SelectTrigger className="text-sm rounded-none border-gray-300 dark:border-zinc-700 bg-transparent focus:ring-0 focus:border-black dark:focus:border-white shadow-none">
                                                <SelectValue placeholder="选择输出模式" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-none border-gray-300 dark:border-zinc-800">
                                                {outputModes.map(mode => (
                                                    <SelectItem key={mode.id} value={mode.id} className="rounded-none cursor-pointer">
                                                        <div className="flex flex-col">
                                                            <span className="font-medium">{mode.name}</span>
                                                            {mode.description && (
                                                                <span className="text-[10px] text-gray-500 mt-0.5">{mode.description}</span>
                                                            )}
                                                        </div>
                                                    </SelectItem>
                                                ))}
                                                {outputModes.length === 0 && (
                                                    <SelectItem value="normal" className="rounded-none">普通模式</SelectItem>
                                                )}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="border-b border-gray-200 dark:border-zinc-800 my-4"></div>

                                <div className="flex gap-2">
                                    {/* KB Manager Button */}
                                    <Button
                                        variant="outline"
                                        className="flex-1 rounded-none border border-gray-300 dark:border-zinc-700 bg-transparent text-gray-700 dark:text-gray-300 hover:border-gray-500 hover:text-black dark:hover:text-white shadow-none text-xs tracking-wide group"
                                        onClick={() => setOpenKBManager(true)}
                                    >
                                        <Database className="w-3.5 h-3.5 mr-2 opacity-70 group-hover:opacity-100" />
                                        知识库
                                    </Button>

                                    {/* Agent Skills Button */}
                                    <Button
                                        variant="outline"
                                        className="flex-[1.5] rounded-none border border-gray-300 dark:border-zinc-700 bg-transparent text-gray-700 dark:text-gray-300 hover:border-gray-500 hover:text-black dark:hover:text-white shadow-none text-xs tracking-wide group"
                                        onClick={() => setOpenAgentSkills(true)}
                                    >
                                        <Zap className="w-3.5 h-3.5 mr-2 opacity-70 group-hover:opacity-100" />
                                        技能配置
                                    </Button>
                                </div>

                            </div>
                        </ScrollArea>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}
