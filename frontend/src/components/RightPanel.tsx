
import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Settings, Database, Upload, Loader2, Bell, RefreshCw, Folder, FolderPlus, Zap } from "lucide-react"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import { cn } from "@/lib/utils"
import { FileTree } from "./FileTree"
// FIX: Use import type for FileNode
import { fetchFileTree, setFileLock, createDirectory, deleteFileItem, renameFileItem, uploadWorkspaceFiles } from "@/lib/api"
import type { FileNode } from "@/lib/api"

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"

// Components
import { AgentSettingsModal } from "./AgentSettingsModal"
import { KnowledgeBaseModal } from "./KnowledgeBaseModal"
import { PendingChangesList } from "./PendingChangesList"
import { GroupPanel } from "./GroupPanel"

import { AgentSkillsModal } from "./AgentSkillsModal"

export function RightPanel() {
    const { currentWorkspaceId, currentAgentId, currentGroupId, language, pendingChanges } = useStore()
    const t = translations[language].rightPanel

    // File Trees
    const [sharedTree, setSharedTree] = useState<FileNode[]>([])
    const [privateTree, setPrivateTree] = useState<FileNode[]>([])
    const [archivesTree, setArchivesTree] = useState<FileNode[]>([])

    const [isUploading, setIsUploading] = useState(false)
    const [isLoadingFiles, setIsLoadingFiles] = useState(false)
    const [openAgentSettings, setOpenAgentSettings] = useState(false)
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
        // Construct new path. 
        const pathParts = renameTarget.path.split('/')
        pathParts.pop() // remove old name
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
        // clean path
        const fullPath = newFolderParent ? `${newFolderParent}/${newFolderName}` : newFolderName
        await createDirectory(fullPath)
        setIsNewFolderOpen(false)
        refreshAll()
    }

    // Drag and Drop Move Handler
    const handleMoveFile = async (sourcePath: string, targetFolder: string) => {
        // Source: "shared/uploads/file.txt"
        // Target: "shared/uploads/docs" or just "shared/uploads"

        const fileName = sourcePath.split('/').pop()
        if (!fileName) return

        let newPath = targetFolder ? `${targetFolder}/${fileName}` : fileName

        // Prevent moving to self
        if (newPath === sourcePath) return

        console.log("Move attempt: ", { sourcePath, targetFolder, newPath });

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

    return (
        <div className="h-full bg-muted/10 border-l flex flex-col relative">

            {/* Modals */}
            <AgentSettingsModal open={openAgentSettings} onOpenChange={setOpenAgentSettings} />
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
                        <TabsTrigger value="files">{t.files}</TabsTrigger>
                        <TabsTrigger value="actions" className="relative">
                            {t.actions}
                            {pendingChanges.length > 0 && (
                                <span className="absolute top-1 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                            )}
                        </TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex-1 overflow-hidden">


                    {/* FILES TAB */}
                    <TabsContent value="files" className="h-full m-0 flex flex-col">
                        <div className="p-3 grid grid-cols-3 gap-2 border-b">
                            <Button variant="outline" size="sm" onClick={() => setOpenAgentSettings(true)}>
                                <Settings className="w-4 h-4 mr-2" />
                                {t.agentSettings}
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => setOpenKBManager(true)}>
                                <Database className="w-4 h-4 mr-2" />
                                {t.kbManager}
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => setOpenAgentSkills(true)} className="border-amber-200 text-amber-700 bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/30 dark:border-amber-900/50">
                                <Zap className="w-4 h-4 mr-2 text-amber-500" />
                                Agent Skills
                            </Button>
                        </div>

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
                    </TabsContent>

                    {/* ACTIONS TAB */}
                    <TabsContent value="actions" className="h-full m-0 flex flex-col bg-background/30">
                        <div className="p-3 border-b flex items-center gap-2 font-semibold text-sm bg-muted/40 sticky top-0 z-10">
                            <Bell className="w-4 h-4 text-orange-500" />
                            {t.pendingChanges}
                        </div>
                        <ScrollArea className="flex-1">
                            <PendingChangesList />
                        </ScrollArea>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}
