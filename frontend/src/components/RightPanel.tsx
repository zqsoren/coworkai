
import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Database, Upload, Loader2, Bell, RefreshCw, Folder, FolderPlus, Zap, Save, Edit2, Wrench, Plug, FileText, Check, Clock, CalendarDays, Timer } from "lucide-react"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { FileTree } from "./FileTree"
import { FileEditorModal } from "./FileEditorModal"
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
import { AgentSkillsModal, TOOL_LABELS, SKILL_LABELS } from "./AgentSkillsModal"
import { ScheduleTaskPanel, taskSummary } from "./ScheduleTaskPanel"
import { fetchScheduledTasks } from "@/lib/api"
import type { ScheduledTask } from "@/lib/api"

// Robot Avatar Options
import avatar01 from "@/assets/avatars/231b51a230ee2bcb8d56c9d918847690.jpg"
import avatar02 from "@/assets/avatars/2fcccc9fcbff12269bcf47736f167b5e.jpg"
import avatar03 from "@/assets/avatars/321eea732004543f1be3deb2e3f5b0cf.jpg"
import avatar04 from "@/assets/avatars/3514a0df6a746f35230fa0700b8ddd76.jpg"
import avatar05 from "@/assets/avatars/450dc7b4510448c25c61cf089cdb4ce3.jpg"
import avatar06 from "@/assets/avatars/4bbbd6736f1569657a23d6760b232fc8.jpg"
import avatar07 from "@/assets/avatars/6e0ef442ffea821399cc6ab1191458f0.jpg"
import avatar08 from "@/assets/avatars/761ff68cdfd35f76d0e979791b20449b.jpg"
import avatar09 from "@/assets/avatars/7d2f249c86e751939a4bde60bfdc2b66.jpg"
import avatar10 from "@/assets/avatars/94a60fd9ab2302b53f1ea3c4d2c8c331.jpg"
import avatar11 from "@/assets/avatars/9c703dcccf96eda6b02822e782589c2f.jpg"
import avatar12 from "@/assets/avatars/beea5fc1ac172ecd3173040c3c796eef.jpg"
import avatar13 from "@/assets/avatars/d7b0acd01ec78dc718acc54ef8ec5338.jpg"
import avatar14 from "@/assets/avatars/e7c4b74449f1db87bcb864f9f46d1aed.jpg"
import avatar15 from "@/assets/avatars/f44fbbe7119bf9231b8419b73f4cf140.jpg"

const AVATAR_OPTIONS = [
    { id: "avatar-01", image: avatar01 },
    { id: "avatar-02", image: avatar02 },
    { id: "avatar-03", image: avatar03 },
    { id: "avatar-04", image: avatar04 },
    { id: "avatar-05", image: avatar05 },
    { id: "avatar-06", image: avatar06 },
    { id: "avatar-07", image: avatar07 },
    { id: "avatar-08", image: avatar08 },
    { id: "avatar-09", image: avatar09 },
    { id: "avatar-10", image: avatar10 },
    { id: "avatar-11", image: avatar11 },
    { id: "avatar-12", image: avatar12 },
    { id: "avatar-13", image: avatar13 },
    { id: "avatar-14", image: avatar14 },
    { id: "avatar-15", image: avatar15 },
]

/** 随机选一个头像 ID（创建 Agent 时使用）*/
export function getRandomAvatarId() {
    return AVATAR_OPTIONS[Math.floor(Math.random() * AVATAR_OPTIONS.length)].id
}

/** 根据 ID 获取头像图片 URL */
export function getAvatarImage(id: string) {
    const found = AVATAR_OPTIONS.find(a => a.id === id)
    return found?.image || AVATAR_OPTIONS[0].image
}

export function RightPanel() {
    const { currentWorkspaceId, currentAgentId, currentGroupId, language, pendingChanges, agents, updateAgent, listFiles } = useStore()
    const t = translations[language].rightPanel

    // File Trees
    const [sharedTree, setSharedTree] = useState<FileNode[]>([])
    const [privateTree, setPrivateTree] = useState<FileNode[]>([])
    const [archivesTree, setArchivesTree] = useState<FileNode[]>([])

    const [isUploading, setIsUploading] = useState(false)
    const [isLoadingFiles, setIsLoadingFiles] = useState(false)
    const [openAgentSkills, setOpenAgentSkills] = useState(false)
    const [openKBManager, setOpenKBManager] = useState(false)
    const [openSchedule, setOpenSchedule] = useState(false)
    const [scheduleTasks, setScheduleTasks] = useState<ScheduledTask[]>([])

    // File Editor Modal
    const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null)
    const [isFileEditorOpen, setIsFileEditorOpen] = useState(false)

    // New Folder Dialog
    const [isNewFolderOpen, setIsNewFolderOpen] = useState(false)
    const [newFolderParent, setNewFolderParent] = useState("")
    const [newFolderName, setNewFolderName] = useState("")

    // Rename Dialog
    const [isRenameOpen, setIsRenameOpen] = useState(false)
    const [renameTarget, setRenameTarget] = useState<FileNode | null>(null)
    const [renameNewName, setRenameNewName] = useState("")

    // Inline Agent Settings State
    const [isEditingName, setIsEditingName] = useState(false)
    const [kbFiles, setKbFiles] = useState<string[]>([])
    const [agentName, setAgentName] = useState("")
    const [agentPrompt, setAgentPrompt] = useState("")
    const [agentModel, setAgentModel] = useState("")
    const [agentProviderId, setAgentProviderId] = useState("")
    const [agentPersonaMode, setAgentPersonaMode] = useState("normal")
    const [agentAvatar, setAgentAvatar] = useState(() => getRandomAvatarId())
    const [showAvatarPicker, setShowAvatarPicker] = useState(false)
    const [providers, setProviders] = useState<any[]>([])
    const [outputModes, setOutputModes] = useState<OutputMode[]>([])
    const [isSaving, setIsSaving] = useState(false)
    const [saveMessage, setSaveMessage] = useState<string | null>(null)

    const agent = agents.find(a => a.id === currentAgentId)

    // Fetch KB files when agent changes
    useEffect(() => {
        if (currentAgentId) {
            listFiles("knowledge_base/processed").then(res => setKbFiles(res || [])).catch(console.error)
        }
    }, [currentAgentId, listFiles])

    // Fetch scheduled tasks when agent changes
    useEffect(() => {
        if (currentAgentId) {
            fetchScheduledTasks(currentAgentId).then(res => setScheduleTasks(res || [])).catch(console.error)
        }
    }, [currentAgentId, openSchedule])

    // Load agent settings when agent changes
    useEffect(() => {
        if (agent) {
            setAgentName(agent.name || "")
            setAgentPrompt(agent.system_prompt || "")
            setAgentProviderId(agent.provider_id || "")
            setAgentModel(agent.model_name || "")
            setAgentPersonaMode(agent.persona_mode || "normal")
            setAgentAvatar((agent as any).avatar || getRandomAvatarId())
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

    // Auto-sync model from provider and persist to DB
    useEffect(() => {
        const selectedProvider = providers.find(p => p.id === agentProviderId)
        if (selectedProvider && (!agentModel || (agent && agent.provider_id !== agentProviderId))) {
            const newModel = selectedProvider.models?.[0] || ""
            setAgentModel(newModel)
            // 同步保存 model_name 到数据库
            if (currentAgentId && newModel) {
                updateAgent(currentAgentId, { provider_id: agentProviderId, model_name: newModel } as any).catch(e => console.error(e))
            }
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
            {currentAgentId && currentWorkspaceId && (
                <ScheduleTaskPanel
                    open={openSchedule}
                    onOpenChange={setOpenSchedule}
                    agentId={currentAgentId}
                    workspaceId={currentWorkspaceId}
                />
            )}

            {/* File Editor Modal */}
            <FileEditorModal
                open={isFileEditorOpen}
                onOpenChange={setIsFileEditorOpen}
                filePath={selectedFilePath}
                onSaved={refreshAll}
            />

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
                    <TabsContent value="files" className="absolute inset-0 m-0 data-[state=active]:flex flex-col overflow-auto data-[state=inactive]:hidden">

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
                                            onSelect={(node) => { if (!node.is_dir) { setSelectedFilePath(node.path); setIsFileEditorOpen(true) } }}
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
                                            onSelect={(node) => { if (!node.is_dir) { setSelectedFilePath(node.path); setIsFileEditorOpen(true) } }}
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
                                            onSelect={(node) => { if (!node.is_dir) { setSelectedFilePath(node.path); setIsFileEditorOpen(true) } }}
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
                    <TabsContent value="settings" className="absolute inset-0 m-0 data-[state=active]:flex flex-col overflow-auto bg-white dark:bg-zinc-950 font-sans data-[state=inactive]:hidden">
                        <ScrollArea className="flex-1">
                            <div className="p-5 space-y-6">

                                {/* Avatar + Name Header */}
                                <div className="flex items-center gap-4 pb-4 border-b border-gray-200 dark:border-zinc-800">
                                    <div className="relative">
                                        <button
                                            onClick={() => setShowAvatarPicker(!showAvatarPicker)}
                                            className="w-12 h-12 rounded-lg overflow-hidden hover:ring-2 hover:ring-gray-400 transition-all cursor-pointer border border-gray-300 dark:border-zinc-700"
                                            title="点击更换头像"
                                        >
                                            <img src={currentAvatar.image} alt="avatar" className="w-full h-full object-cover" />
                                        </button>
                                        {/* Avatar Picker Dropdown */}
                                        {showAvatarPicker && (
                                            <div className="absolute top-14 left-0 z-50 bg-white dark:bg-zinc-950 border border-gray-300 dark:border-zinc-800 rounded-xl p-3 w-[240px] shadow-lg">
                                                <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2 font-semibold">更换头像 / AVATAR</div>
                                                <div className="grid grid-cols-5 gap-1.5">
                                                    {AVATAR_OPTIONS.map(opt => (
                                                        <button
                                                            key={opt.id}
                                                            onClick={() => {
                                                                setAgentAvatar(opt.id)
                                                                setShowAvatarPicker(false)
                                                            }}
                                                            className={cn(
                                                                "w-10 h-10 rounded-lg overflow-hidden hover:ring-2 hover:ring-gray-400 transition-all cursor-pointer border-2 border-transparent",
                                                                agentAvatar === opt.id && "border-black dark:border-white ring-2 ring-black dark:ring-white"
                                                            )}
                                                        >
                                                            <img src={opt.image} alt={opt.id} className="w-full h-full object-cover" />
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        {isEditingName ? (
                                            <div className="flex items-center gap-2">
                                                <Input
                                                    value={agentName}
                                                    onChange={(e) => setAgentName(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') {
                                                            setIsEditingName(false)
                                                            handleSaveSettings()
                                                        }
                                                    }}
                                                    autoFocus
                                                    className="text-lg font-semibold border-b border-gray-300 dark:border-zinc-700 shadow-none p-0 h-auto focus-visible:ring-0 bg-transparent rounded-none"
                                                    placeholder="Agent 名称"
                                                />
                                                <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => { setIsEditingName(false); handleSaveSettings() }}>
                                                    <Check className="w-4 h-4 text-green-600" />
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="flex items-center gap-2 group/name cursor-pointer w-fit" onClick={() => setIsEditingName(true)}>
                                                <h2 className="text-lg font-semibold truncate hover:bg-gray-50 dark:hover:bg-zinc-800/50 px-1 py-0.5 -ml-1 rounded transition-colors">{agentName || "未命名 Agent"}</h2>
                                                <Edit2 className="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover/name:opacity-100 transition-opacity" />
                                            </div>
                                        )}
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
                                            className="min-h-[120px] text-sm resize-y rounded-lg border-gray-300 dark:border-zinc-700 bg-transparent focus-visible:ring-0 focus-visible:border-black dark:focus-visible:border-white shadow-none"
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
                                                    className="h-7 px-3 w-auto rounded-lg border border-black dark:border-white bg-white dark:bg-black text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black uppercase tracking-widest text-[10px] font-bold transition-colors shadow-none"
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
                                                    try {
                                                        const prov = providers.find(p => p.id === val)
                                                        const newModel = prov?.models?.[0] || agentModel
                                                        await updateAgent(currentAgentId, { provider_id: val, model_name: newModel } as any)
                                                    } catch (e) { console.error(e) }
                                                }
                                            }}
                                        >
                                            <SelectTrigger className="text-sm rounded-lg border-gray-300 dark:border-zinc-700 bg-transparent focus:ring-0 focus:border-black dark:focus:border-white shadow-none">
                                                <SelectValue placeholder="选择提供商" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-lg border-gray-300 dark:border-zinc-800">
                                                {providers.map(p => (
                                                    <SelectItem key={p.id} value={p.id} className="rounded-md cursor-pointer">{p.name} ({p.type})</SelectItem>
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
                                            <SelectTrigger className="text-sm rounded-lg border-gray-300 dark:border-zinc-700 bg-transparent focus:ring-0 focus:border-black dark:focus:border-white shadow-none">
                                                <SelectValue placeholder="选择输出模式" />
                                            </SelectTrigger>
                                            <SelectContent className="rounded-lg border-gray-300 dark:border-zinc-800">
                                                {outputModes.map(mode => (
                                                    <SelectItem key={mode.id} value={mode.id} className="rounded-md cursor-pointer">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-medium">{mode.name}</span>
                                                            {mode.description && (
                                                                <span className="text-[10px] text-gray-400">— {mode.description}</span>
                                                            )}
                                                        </div>
                                                    </SelectItem>
                                                ))}
                                                {outputModes.length === 0 && (
                                                    <SelectItem value="normal" className="rounded-md">普通模式</SelectItem>
                                                )}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="border-b border-gray-200 dark:border-zinc-800 my-4"></div>

                                <div className="space-y-4">
                                    {/* KB Manager Button */}
                                    <div className="space-y-2">
                                        <Button
                                            variant="outline"
                                            className="w-full rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-gray-700 dark:text-gray-300 hover:border-gray-500 hover:text-black dark:hover:text-white shadow-none text-xs tracking-wide group"
                                            onClick={() => setOpenKBManager(true)}
                                        >
                                            <Database className="w-3.5 h-3.5 mr-2 opacity-70 group-hover:opacity-100" />
                                            知识库
                                        </Button>
                                        <div className="mt-1">
                                            {kbFiles.length > 0 ? (
                                                <div className="divide-y divide-gray-100 dark:divide-zinc-800">
                                                    {kbFiles.slice(0, 5).map(f => (
                                                        <div key={f} className="flex items-center justify-between py-[5px] px-1 text-[11px] text-gray-600 dark:text-gray-400">
                                                            <div className="flex items-center gap-2 truncate">
                                                                <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 uppercase tracking-wide shrink-0">KB</span>
                                                                <span className="truncate">{f}</span>
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {kbFiles.length > 5 && <div className="text-[10px] text-gray-400 py-1 pl-1">... 共 {kbFiles.length} 个文件</div>}
                                                </div>
                                            ) : (
                                                <div className="text-xs text-gray-400 italic pl-1">暂无文件，点击上方上传知识库</div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Agent Skills Button */}
                                    <div className="space-y-2">
                                        <Button
                                            variant="outline"
                                            className="w-full rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-gray-700 dark:text-gray-300 hover:border-gray-500 hover:text-black dark:hover:text-white shadow-none text-xs tracking-wide group"
                                            onClick={() => setOpenAgentSkills(true)}
                                        >
                                            <Wrench className="w-3.5 h-3.5 mr-2 opacity-70 group-hover:opacity-100" />
                                            技能配置
                                        </Button>
                                        <div className="mt-1">
                                            {agent && (((agent as any).tools?.length > 0) || ((agent as any).skills?.length > 0) || ((agent as any).mcp_servers?.length > 0)) ? (
                                                <div className="divide-y divide-gray-100 dark:divide-zinc-800">
                                                    {((agent as any).skills || []).slice(0, 5).map((s: string) => (
                                                        <div key={`skill-${s}`} className="flex items-center py-[5px] px-1 text-[11px] text-gray-600 dark:text-gray-400 gap-2">
                                                            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 shrink-0">技能</span>
                                                            <span className="truncate">{SKILL_LABELS[s] || s}</span>
                                                        </div>
                                                    ))}
                                                    {((agent as any).mcp_servers || []).filter((s: any) => s.enabled).slice(0, 5).map((m: any) => (
                                                        <div key={`mcp-${m.id}`} className="flex items-center py-[5px] px-1 text-[11px] text-gray-600 dark:text-gray-400 gap-2">
                                                            {m.icon && typeof m.icon === 'string' && (m.icon.includes('/') || m.icon.includes('.')) ? (
                                                                <img src={m.icon} alt={m.name} className="w-4 h-4 rounded-sm object-cover shrink-0" />
                                                            ) : m.icon ? (
                                                                <span className="text-sm shrink-0">{m.icon}</span>
                                                            ) : (
                                                                <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 shrink-0">MCP</span>
                                                            )}
                                                            <span className="truncate">{m.name}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-xs text-gray-400 italic pl-1">暂未配置任何工具或技能</div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Scheduled Tasks Button */}
                                    <div className="space-y-2">
                                        <Button
                                            variant="outline"
                                            className="w-full rounded-lg border border-gray-300 dark:border-zinc-700 bg-transparent text-gray-700 dark:text-gray-300 hover:border-gray-500 hover:text-black dark:hover:text-white shadow-none text-xs tracking-wide group"
                                            onClick={() => setOpenSchedule(true)}
                                        >
                                            <Clock className="w-3.5 h-3.5 mr-2 opacity-70 group-hover:opacity-100" />
                                            定时任务
                                        </Button>
                                        <div className="pl-1">
                                            {scheduleTasks.length > 0 ? (
                                                <div className="space-y-1">
                                                    {scheduleTasks.slice(0, 3).map(t => (
                                                        <div key={t.id} className="flex items-center gap-2 text-[11px] text-gray-500">
                                                            {t.mode === 'calendar' ? <CalendarDays className="w-3 h-3 text-blue-400 shrink-0" /> : <Timer className="w-3 h-3 text-orange-400 shrink-0" />}
                                                            <span className={t.enabled ? '' : 'line-through opacity-50'}>{taskSummary(t)}</span>
                                                        </div>
                                                    ))}
                                                    {scheduleTasks.length > 3 && <div className="text-[10px] text-gray-400 pl-5">... 共 {scheduleTasks.length} 条任务</div>}
                                                </div>
                                            ) : (
                                                <div className="text-xs text-gray-400 italic">暂无定时任务</div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                            </div>
                        </ScrollArea>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}
