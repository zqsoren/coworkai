import { useState, useEffect } from "react"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, Save, FileText } from "lucide-react"
import { fetchFileContent, saveFileContent } from "@/lib/api"
import { cn } from "@/lib/utils"

interface FileEditorModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    filePath: string | null
    onSaved?: () => void
}

export function FileEditorModal({ open, onOpenChange, filePath, onSaved }: FileEditorModalProps) {
    const [content, setContent] = useState("")
    const [originalContent, setOriginalContent] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [saveMsg, setSaveMsg] = useState<string | null>(null)

    // 加载文件内容
    useEffect(() => {
        if (!open || !filePath) return
        setIsLoading(true)
        setSaveMsg(null)
        fetchFileContent(filePath)
            .then(res => {
                setContent(res.content)
                setOriginalContent(res.content)
            })
            .catch(err => {
                console.error("Failed to load file:", err)
                setContent("⚠️ 无法加载文件内容")
            })
            .finally(() => setIsLoading(false))
    }, [open, filePath])

    const hasChanges = content !== originalContent

    const handleSave = async () => {
        if (!filePath || !hasChanges) return
        setIsSaving(true)
        setSaveMsg(null)
        try {
            await saveFileContent(filePath, content)
            setOriginalContent(content)
            setSaveMsg("保存成功")
            onSaved?.()
            setTimeout(() => setSaveMsg(null), 2000)
        } catch (err) {
            console.error("Save failed:", err)
            setSaveMsg("保存失败")
            setTimeout(() => setSaveMsg(null), 3000)
        } finally {
            setIsSaving(false)
        }
    }

    const fileName = filePath?.split("/").pop() || "文件"

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 rounded-none border-gray-300 dark:border-zinc-700">
                {/* Header */}
                <DialogHeader className="px-5 py-3 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900/50">
                    <DialogTitle className="flex items-center gap-2 text-sm font-medium">
                        <FileText className="w-4 h-4 text-muted-foreground" />
                        <span className="truncate">{fileName}</span>
                        <span className="text-[10px] text-muted-foreground font-normal ml-auto truncate max-w-[200px]">{filePath}</span>
                    </DialogTitle>
                </DialogHeader>

                {/* Content */}
                <div className="flex-1 overflow-hidden p-4">
                    {isLoading ? (
                        <div className="flex items-center justify-center h-40">
                            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                            <span className="ml-2 text-sm text-muted-foreground">加载中...</span>
                        </div>
                    ) : (
                        <Textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            className="min-h-[400px] max-h-[60vh] text-sm font-mono resize-y rounded-none border-gray-300 dark:border-zinc-700 bg-transparent focus-visible:ring-0 focus-visible:border-black dark:focus-visible:border-white shadow-none"
                            placeholder="文件内容为空"
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-3 border-t border-gray-200 dark:border-zinc-800 flex items-center justify-between bg-gray-50 dark:bg-zinc-900/50">
                    <div className="text-[10px] text-muted-foreground">
                        {hasChanges && <span className="text-orange-500 font-medium">● 未保存的修改</span>}
                    </div>
                    <div className="flex items-center gap-2">
                        {saveMsg && (
                            <span className={cn("text-[11px] font-medium", saveMsg.includes("成功") ? "text-green-600" : "text-red-500")}>
                                {saveMsg}
                            </span>
                        )}
                        <Button
                            onClick={handleSave}
                            disabled={isSaving || !hasChanges}
                            className="h-7 px-4 rounded-none border border-black dark:border-white bg-white dark:bg-black text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black uppercase tracking-widest text-[10px] font-bold transition-colors shadow-none disabled:opacity-40"
                        >
                            {isSaving ? (
                                <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                            ) : (
                                <Save className="mr-1.5 h-3 w-3" />
                            )}
                            {isSaving ? "SAVING..." : "SAVE"}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}
