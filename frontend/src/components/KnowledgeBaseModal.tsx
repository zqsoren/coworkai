import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import { Loader2, Upload, FileText, Trash2, ArrowRight, CheckCircle } from "lucide-react"

interface Props {
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function KnowledgeBaseModal({ open, onOpenChange }: Props) {
    const { language, listFiles, uploadFiles, deleteFile, processKnowledge } = useStore()
    const t = translations[language].kbModal

    const [uploadedFiles, setUploadedFiles] = useState<string[]>([])
    const [processedFiles, setProcessedFiles] = useState<string[]>([])

    const [isProcessing, setIsProcessing] = useState(false)
    const [isUploading, setIsUploading] = useState(false)

    const refreshFiles = async () => {
        // Fetch both lists
        const [up, pro] = await Promise.all([
            listFiles("knowledge_base/uploads"),
            listFiles("knowledge_base/processed")
        ])
        setUploadedFiles(up || [])
        setProcessedFiles(pro || [])
    }

    useEffect(() => {
        if (open) {
            refreshFiles()
        }
    }, [open])

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return
        setIsUploading(true)
        try {
            // "knowledge_base" type maps to uploads folder in backend
            await uploadFiles("knowledge_base", Array.from(e.target.files))
            await refreshFiles()
        } catch (err) {
            console.error(err)
        } finally {
            setIsUploading(false)
        }
    }

    const handleDelete = async (filename: string, type: string) => {
        if (!confirm("Delete file?")) return
        await deleteFile(type, filename)
        refreshFiles()
    }

    const handleProcess = async () => {
        setIsProcessing(true)
        try {
            await processKnowledge()
            await refreshFiles()
        } catch (err) {
            console.error(err)
            alert("Processing failed")
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[800px] h-[80vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle>{t.title}</DialogTitle>
                    <DialogDescription>
                        Manage your agent's knowledge base. Upload documents, then process them to enable RAG.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-hidden grid grid-cols-2 gap-4">

                    {/* LEFT: Unprocessed / Uploads */}
                    <div className="flex flex-col border rounded-md bg-muted/10">
                        <div className="p-3 border-b bg-muted/20 flex justify-between items-center font-medium">
                            <span className="flex items-center gap-2">
                                <Upload className="w-4 h-4 text-muted-foreground" />
                                Unprocessed Uploads
                            </span>
                            <div className="relative">
                                <Input
                                    type="file"
                                    multiple
                                    className="hidden"
                                    id="kb-upload-btn"
                                    onChange={handleUpload}
                                    disabled={isUploading}
                                />
                                <label htmlFor="kb-upload-btn">
                                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0" asChild disabled={isUploading}>
                                        <span className="cursor-pointer">
                                            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                                        </span>
                                    </Button>
                                </label>
                            </div>
                        </div>

                        <ScrollArea className="flex-1 p-2">
                            {uploadedFiles.length === 0 && (
                                <div className="text-center text-muted-foreground text-sm py-10 italic">
                                    No unprocessed files.<br />Upload documents to start.
                                </div>
                            )}
                            {uploadedFiles.map(f => (
                                <div key={f} className="flex items-center justify-between p-2 rounded-md hover:bg-background text-sm group border mb-2 bg-background/50">
                                    <div className="flex items-center gap-2 truncate">
                                        <FileText className="w-4 h-4 text-orange-500" />
                                        <span className="truncate">{f}</span>
                                    </div>
                                    <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100" onClick={() => handleDelete(f, "knowledge_base/uploads")}>
                                        <Trash2 className="w-3 h-3 text-destructive" />
                                    </Button>
                                </div>
                            ))}
                        </ScrollArea>

                        <div className="p-3 border-t bg-background">
                            <Button
                                className="w-full"
                                size="sm"
                                onClick={handleProcess}
                                disabled={uploadedFiles.length === 0 || isProcessing}
                            >
                                {isProcessing ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Processing...
                                    </>
                                ) : (
                                    <>
                                        Split & Process <ArrowRight className="w-4 h-4 ml-2" />
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>

                    {/* RIGHT: Processed */}
                    <div className="flex flex-col border rounded-md bg-muted/10">
                        <div className="p-3 border-b bg-muted/20 flex justify-between items-center font-medium">
                            <span className="flex items-center gap-2">
                                <CheckCircle className="w-4 h-4 text-green-600" />
                                Processed Documents
                            </span>
                            <span className="text-xs text-muted-foreground">{processedFiles.length} files</span>
                        </div>

                        <ScrollArea className="flex-1 p-2">
                            {processedFiles.length === 0 && (
                                <div className="text-center text-muted-foreground text-sm py-10 italic">
                                    No processed documents.
                                </div>
                            )}
                            {processedFiles.map(f => (
                                <div key={f} className="flex items-center justify-between p-2 rounded-md hover:bg-background text-sm group border mb-2 bg-background/50">
                                    <div className="flex items-center gap-2 truncate">
                                        <FileText className="w-4 h-4 text-green-600" />
                                        <span className="truncate">{f}</span>
                                    </div>
                                    {/* Ideally we don't delete processed files easily without removing from DB, allowing delete here for now */}
                                    <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100" onClick={() => handleDelete(f, "knowledge_base/processed")}>
                                        <Trash2 className="w-3 h-3 text-destructive" />
                                    </Button>
                                </div>
                            ))}
                        </ScrollArea>
                    </div>

                </div>

            </DialogContent>
        </Dialog>
    )
}
