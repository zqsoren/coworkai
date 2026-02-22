import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageSquare, Trash2, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { sessionManager, type SessionMeta } from "@/utils/sessionManager"
import { useStore } from "@/store"

interface Props {
    open: boolean
    onOpenChange: (open: boolean) => void
    contextId: string // agentId or groupId
    onSelectSession: (sessionId: string) => void
    currentSessionId: string | null
}

export function SessionHistoryModal({ open, onOpenChange, contextId, onSelectSession, currentSessionId }: Props) {
    const [sessions, setSessions] = useState<SessionMeta[]>([])
    const { language } = useStore()

    const reload = () => {
        setSessions(sessionManager.listSessions(contextId))
    }

    useEffect(() => {
        if (open) reload()
    }, [open, contextId])

    const handleDelete = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation()
        if (confirm("确定要删除这条历史记录吗？")) {
            sessionManager.deleteSession(contextId, sessionId)
            reload()
        }
    }

    const handleSelect = (sessionId: string) => {
        onSelectSession(sessionId)
        onOpenChange(false)
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[480px] max-h-[72vh] flex flex-col p-0 gap-0">
                <DialogHeader className="px-5 pt-5 pb-3 border-b shrink-0">
                    <DialogTitle className="flex items-center gap-2 text-base">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        历史会话
                    </DialogTitle>
                </DialogHeader>

                {sessions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
                        <MessageSquare className="h-10 w-10 text-muted-foreground/30" />
                        <p className="text-sm text-muted-foreground">暂无历史会话</p>
                        <p className="text-xs text-muted-foreground/60">发起对话后，点击 + 新建会话即可保存历史</p>
                    </div>
                ) : (
                    <ScrollArea className="flex-1 min-h-0">
                        <div className="p-3 space-y-1.5">
                            {sessions.map((session) => (
                                <div
                                    key={session.id}
                                    onClick={() => handleSelect(session.id)}
                                    className={cn(
                                        "group relative flex flex-col gap-1 p-3 rounded-lg cursor-pointer transition-colors",
                                        "hover:bg-muted/60 border",
                                        session.id === currentSessionId
                                            ? "bg-blue-50/60 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800"
                                            : "bg-muted/20 border-transparent hover:border-muted"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <p className="font-medium text-sm leading-tight line-clamp-1 flex-1">
                                            {session.title}
                                        </p>
                                        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-6 w-6 text-destructive hover:text-destructive hover:bg-destructive/10"
                                                onClick={(e) => handleDelete(e, session.id)}
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    </div>
                                    {session.preview && (
                                        <p className="text-xs text-muted-foreground line-clamp-1">{session.preview}</p>
                                    )}
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground/60 mt-0.5">
                                        <MessageSquare className="h-3 w-3" />
                                        <span>{session.messageCount} 条消息</span>
                                        <span>·</span>
                                        <span>{sessionManager.formatTime(session.updatedAt)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </DialogContent>
        </Dialog>
    )
}
