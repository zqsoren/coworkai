import { useEffect, useRef, useState } from "react"
import type { Agent } from "@/lib/api"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Loader2, Plus, ChevronDown, Copy, Crown, Clock, MessageSquarePlus, Wrench, CheckCircle2, AlertCircle } from "lucide-react"
import { useStore } from "@/store"
import { cn } from "@/lib/utils"
import { translations } from "@/lib/i18n"
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'
import { SessionHistoryModal } from "@/components/SessionHistoryModal"

import { parseMessage } from '@/utils/messageParser'


// Hook for typewriter effect
function useTypewriterEffect(text: string, speed: number = 10) {
    const [displayedText, setDisplayedText] = useState("")
    const [isComplete, setIsComplete] = useState(false)

    useEffect(() => {
        if (!text) return

        setDisplayedText("")
        setIsComplete(false)
        let currentIndex = 0

        const interval = setInterval(() => {
            if (currentIndex < text.length) {
                // Show 10 characters at a time
                const nextIndex = Math.min(currentIndex + speed, text.length)
                setDisplayedText(text.substring(0, nextIndex))
                currentIndex = nextIndex
            } else {
                setIsComplete(true)
                clearInterval(interval)
            }
        }, 100) // 100ms interval

        return () => clearInterval(interval)
    }, [text, speed])

    return { displayedText, isComplete }
}

// Color palette for different agents in group chat
const AGENT_COLORS = [
    { bg: "bg-blue-600", text: "text-white", border: "border-blue-500" },
    { bg: "bg-emerald-600", text: "text-white", border: "border-emerald-500" },
    { bg: "bg-purple-600", text: "text-white", border: "border-purple-500" },
    { bg: "bg-orange-600", text: "text-white", border: "border-orange-500" },
    { bg: "bg-pink-600", text: "text-white", border: "border-pink-500" },
    { bg: "bg-teal-600", text: "text-white", border: "border-teal-500" },
]

function getAgentColor(_name: string, index: number) {
    return AGENT_COLORS[index % AGENT_COLORS.length]
}

export function Chat() {
    const {
        messages, isLoading, currentAgentId, currentGroupId,
        agents, groups, sendChatMessage, language,
        generateWorkflowPlan,
        chatMode, setChatMode,
        groupMessages, loadGroupMessages,
        startNewSession, switchSession, currentSessionId,
        activityLog, activeAgents,
    } = useStore()
    const t = translations[language].chat

    const currentAgent = agents.find(a => a.id === currentAgentId)
    const currentGroup = groups.find(g => g.id === currentGroupId)

    const isGroupMode = !!currentGroupId
    const hasTarget = !!currentAgentId || !!currentGroupId

    const [input, setInput] = useState("")
    const [isUploading, setIsUploading] = useState(false) // New state
    const scrollRef = useRef<HTMLDivElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null) // New ref
    const [isDragOver, setIsDragOver] = useState(false) // New drag state
    const [showHistoryModal, setShowHistoryModal] = useState(false)

    // [NEW] Mention Feature State
    const [showMentionList, setShowMentionList] = useState(false)
    const [mentionQuery, setMentionQuery] = useState("")
    const [mentionIndex, setMentionIndex] = useState(0)
    const inputRef = useRef<HTMLTextAreaElement>(null)
    const highlightRef = useRef<HTMLDivElement>(null)

    // [NEW] File Reference Mapping
    const [fileReferences, setFileReferences] = useState<Record<string, string>>({})

    // Build agent name -> color map for group chat
    const agentColorMap = new Map<string, typeof AGENT_COLORS[0]>()
    if (currentGroup) {
        currentGroup.members.forEach((memberId, idx) => {
            const agent = agents.find(a => a.id === memberId)
            if (agent) {
                agentColorMap.set(agent.name, getAgentColor(agent.name, idx))
            }
        })
    }

    // [NEW] Mention Feature Logic
    const availableMembers = currentGroup && isGroupMode
        ? currentGroup.members
            .map(id => agents.find(a => a.id === id))
            .filter(a => a && a.name.toLowerCase().includes(mentionQuery.toLowerCase())) as Agent[]
        : []

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newValue = e.target.value
        setInput(newValue)

        const cursorPosition = e.target.selectionStart
        const textBeforeCursor = newValue.slice(0, cursorPosition)
        const lastAtSymbolIndex = textBeforeCursor.lastIndexOf("@")

        if (lastAtSymbolIndex !== -1) {
            // Check if there are spaces between @ and cursor (allow easy multi-word matching later, but for now strict)
            // Or simple: Just check if we are "in" a mention
            const query = textBeforeCursor.slice(lastAtSymbolIndex + 1)
            // Only trigger if no spaces (simple name matching) or short
            if (!query.includes(" ")) {
                setShowMentionList(true)
                setMentionQuery(query)
                setMentionIndex(0) // Reset selection
                return
            }
        }
        setShowMentionList(false)
    }

    const insertMention = (agentName: string) => {
        if (!inputRef.current) return

        const cursorPosition = inputRef.current.selectionStart
        const textBeforeCursor = input.slice(0, cursorPosition)
        const lastAtSymbolIndex = textBeforeCursor.lastIndexOf("@")

        const textAfterCursor = input.slice(cursorPosition)
        const newText = input.slice(0, lastAtSymbolIndex) + `@${agentName} ` + textAfterCursor

        setInput(newText)
        setShowMentionList(false)

        // Restore focus and cursor (approximate)
        setTimeout(() => {
            if (inputRef.current) {
                inputRef.current.focus()
            }
        }, 0)
    }

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (showMentionList && availableMembers.length > 0) {
            if (e.key === "ArrowUp") {
                e.preventDefault()
                setMentionIndex(prev => (prev - 1 + availableMembers.length) % availableMembers.length)
            } else if (e.key === "ArrowDown") {
                e.preventDefault()
                setMentionIndex(prev => (prev + 1) % availableMembers.length)
            } else if (e.key === "Enter" || e.key === "Tab") {
                e.preventDefault()
                insertMention(availableMembers[mentionIndex].name)
            } else if (e.key === "Escape") {
                setShowMentionList(false)
            }
        }

        if (e.key === "Enter" && !e.shiftKey && !showMentionList) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files
        if (!files || files.length === 0) return

        const file = files[0]
        setIsUploading(true)

        try {
            const workspaceId = useStore.getState().currentWorkspaceId
            // Use 'shared' agentId for chat uploads to map to shared/uploads
            const targetAgentId = isGroupMode ? "shared" : (currentAgentId || "shared")

            const { uploadFiles } = await import("@/lib/api")
            await uploadFiles(workspaceId!, targetAgentId, "chat_upload", [file])

            // Append file reference to input
            setInput(prev => prev + ` [文件: ${file.name}] `)

            // Reset input
            if (fileInputRef.current) fileInputRef.current.value = ""

        } catch (error) {
            console.error("Upload failed", error)
            // maybe show toast
        } finally {
            setIsUploading(false)
        }
    }

    // [NEW] Drag and Drop Handlers for Chat Input
    const handleDragOver = (e: React.DragEvent) => {
        if (e.dataTransfer.types.includes("application/vnd.agentos.filepath")) {
            e.preventDefault()
            e.dataTransfer.dropEffect = "copy"
            setIsDragOver(true)
        }
    }

    const handleDragLeave = () => {
        setIsDragOver(false)
    }

    const handleDrop = (e: React.DragEvent) => {
        setIsDragOver(false)
        const filepath = e.dataTransfer.getData("application/vnd.agentos.filepath")
        const filename = e.dataTransfer.getData("application/vnd.agentos.filename")
        if (filepath && filename) {
            e.preventDefault()
            const token = `[文件: ${filename}]`

            // Map token to actual path
            setFileReferences(prev => ({ ...prev, [token]: filepath }))

            const tokenWithSpace = token + " "

            // Insert at cursor if textarea focused, otherwise append
            if (textareaRef.current) {
                const start = textareaRef.current.selectionStart
                const end = textareaRef.current.selectionEnd
                const newText = input.substring(0, start) + tokenWithSpace + input.substring(end)
                setInput(newText)

                // Set cursor position after token
                setTimeout(() => {
                    if (textareaRef.current) {
                        textareaRef.current.focus()
                        const newPos = start + tokenWithSpace.length
                        textareaRef.current.setSelectionRange(newPos, newPos)
                    }
                }, 0)
            } else {
                setInput(prev => prev + tokenWithSpace)
            }
        }
    }

    // Auto-scroll


    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: "smooth" })
        }
    }, [messages, isLoading, groupMessages, currentGroupId])

    // Load group messages when switching groups
    useEffect(() => {
        if (currentGroupId) {
            loadGroupMessages(currentGroupId)
        }
    }, [currentGroupId])

    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const handleSendMessage = async () => {
        console.log("[Chat] handleSendMessage called, input:", input, "isLoading:", isLoading)
        if (!input.trim() || isLoading) return

        // Replace visual tokens with actual file paths before sending
        let text = input
        Object.entries(fileReferences).forEach(([token, path]) => {
            // Replace all occurrences of the token with the actual path
            text = text.split(token).join(path)
        })

        setInput("")
        // Clear references after sending
        setFileReferences({})

        // Reset textarea height immediately after clearing input
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = '50px'
        }

        // In group mode, check chatMode to decide behavior
        if (isGroupMode) {
            console.log("[Chat] Group mode, chatMode:", chatMode)
            if (chatMode === 'workflow') {
                console.log("[Chat] Calling generateWorkflowPlan...")
                await generateWorkflowPlan(text)
            } else {
                // Legacy step-by-step mode
                console.log("[Chat] Calling sendChatMessage (legacy)...")
                await sendChatMessage(text)
            }
        } else {
            console.log("[Chat] Single agent mode, calling sendChatMessage...")
            await sendChatMessage(text)
        }
        console.log("[Chat] handleSendMessage completed")
    }


    const displayName = isGroupMode
        ? (currentGroup?.name || "Group Chat")
        : (currentAgent?.name || "Agent")

    const welcomeMode = isGroupMode
        ? (!groupMessages[currentGroupId!] || groupMessages[currentGroupId!].length === 0)
        : (messages.length === 0)

    return (
        <div className="flex h-full flex-col relative bg-background overflow-hidden">
            {/* Chat Header */}
            <div className="h-14 border-b flex items-center justify-between bg-background/80 backdrop-blur-sm z-10 shrink-0 relative px-4">
                <div className="flex items-center gap-2">
                    {isGroupMode ? (
                        <div className="hidden" /> // Removed group icon
                    ) : (
                        <div className="hidden" /> // Removed agent avatar
                    )}
                    <div className="flex flex-col">
                        <h3 className="text-sm font-medium">{hasTarget ? displayName : "Select an Agent"}</h3>
                        {isGroupMode && currentGroup && (
                            <span className="text-[10px] text-muted-foreground">
                                {currentGroup.members.length} members
                            </span>
                        )}
                    </div>
                </div>

                {/* Session Buttons - right side */}
                {hasTarget && (
                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                            title="历史会话"
                            onClick={() => setShowHistoryModal(true)}
                        >
                            <Clock className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                            title="新建会话"
                            onClick={() => startNewSession()}
                        >
                            <MessageSquarePlus className="h-4 w-4" />
                        </Button>
                    </div>
                )}
            </div>

            {/* Session History Modal */}
            <SessionHistoryModal
                open={showHistoryModal}
                onOpenChange={setShowHistoryModal}
                contextId={currentAgentId || currentGroupId || ""}
                onSelectSession={switchSession}
                currentSessionId={currentSessionId}
            />

            {/* Chat Area */}
            <ScrollArea className="flex-1 w-full relative">
                <div className="flex flex-col gap-0 pb-48 max-w-3xl mx-auto w-full pt-4">
                    {(isGroupMode ? (groupMessages[currentGroupId!] || []) : messages)
                        .filter(msg => !msg.is_plan && !msg.content.includes("📅 项目计划"))
                        .map((msg, idx) => {
                            const speakerName = msg.name || (msg.role === 'user' ? 'You' : displayName)
                            const agentColor = msg.name ? agentColorMap.get(msg.name) : undefined
                            const isUser = msg.role === 'user'

                            const isSupervisor = msg.name === 'Supervisor'

                            if (msg.is_basket_summary) {
                                return (
                                    <div key={idx} className="flex justify-center my-6 px-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                        <div className="bg-gray-100 rounded-2xl p-6 max-w-2xl w-full shadow-sm">
                                            <div className="text-xs font-bold text-gray-400 mb-4 tracking-widest text-center">汇总信息</div>
                                            <div className="text-left prose prose-sm dark:prose-invert max-w-none break-words text-[15px] leading-relaxed text-gray-800">
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        code({ node, inline, className, children, ...props }: any) {
                                                            const match = /language-(\w+)/.exec(className || '')
                                                            const lang = match ? match[1] : ''
                                                            // If it's a ```markdown or plain ``` block, re-render content as Markdown
                                                            if (!inline && (!lang || lang === 'markdown' || lang === 'md')) {
                                                                return (
                                                                    <div className="border-l-2 border-gray-300 pl-3 my-2">
                                                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                                            {String(children).replace(/\n$/, '')}
                                                                        </ReactMarkdown>
                                                                    </div>
                                                                )
                                                            }
                                                            return !inline && lang ? (
                                                                <SyntaxHighlighter
                                                                    {...props}
                                                                    style={oneLight}
                                                                    language={lang}
                                                                    PreTag="div"
                                                                    customStyle={{ background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0', fontSize: '0.85rem', margin: '1em 0' }}
                                                                >
                                                                    {String(children).replace(/\n$/, '')}
                                                                </SyntaxHighlighter>
                                                            ) : (
                                                                <code {...props} className={cn("bg-muted px-1 py-0.5 rounded font-mono text-sm", className)}>
                                                                    {children}
                                                                </code>
                                                            )
                                                        },
                                                        table({ children, ...props }: any) {
                                                            return (
                                                                <div className="overflow-x-auto my-4 rounded-lg border border-gray-200 shadow-sm">
                                                                    <table {...props} className="min-w-full text-sm">{children}</table>
                                                                </div>
                                                            )
                                                        },
                                                        thead({ children, ...props }: any) {
                                                            return <thead {...props} className="bg-gray-50 border-b border-gray-200">{children}</thead>
                                                        },
                                                        tbody({ children, ...props }: any) {
                                                            return <tbody {...props} className="divide-y divide-gray-100">{children}</tbody>
                                                        },
                                                        tr({ children, ...props }: any) {
                                                            return <tr {...props} className="hover:bg-gray-50/60 transition-colors">{children}</tr>
                                                        },
                                                        th({ children, ...props }: any) {
                                                            return <th {...props} className="px-4 py-2.5 text-left font-semibold text-gray-700 text-xs uppercase tracking-wide">{children}</th>
                                                        },
                                                        td({ children, ...props }: any) {
                                                            return <td {...props} className="px-4 py-2.5 text-gray-700 align-top">{children}</td>
                                                        },
                                                    }}
                                                >
                                                    {msg.content}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                    </div>
                                )
                            }

                            return (
                                <div key={idx} className={cn(
                                    "flex gap-6 p-8 border-b border-gray-100/50 transition-colors animate-in fade-in slide-in-from-bottom-2 duration-300 hover:bg-gray-50/30",
                                    // Style 01: Clean container
                                )}>
                                    <Avatar className="h-8 w-8 mt-0.5 shrink-0 rounded-md">
                                        <AvatarFallback className={cn(
                                            "text-[10px] flex items-center justify-center rounded-md font-medium",
                                            isUser
                                                ? "bg-gray-700 text-white"
                                                : isSupervisor
                                                    ? "bg-amber-100 text-amber-600"
                                                    : agentColor
                                                        ? `${agentColor.bg} ${agentColor.text}`
                                                        : "bg-blue-600 text-white"
                                        )}>
                                            {isUser ? 'U' : isSupervisor ? <Crown className="h-3.5 w-3.5" /> : speakerName.substring(0, 2).toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>

                                    <div className="flex-1 min-w-0 space-y-1 overflow-hidden select-text">
                                        <MessageContent
                                            content={msg.content}
                                            role={msg.role}
                                            name={msg.name}
                                            agents={agents}
                                            speakerName={speakerName}
                                            agentColor={agentColor}
                                            isUser={isUser}
                                            isGroupMode={isGroupMode}
                                            shouldAnimate={msg.shouldAnimate}
                                        />
                                    </div>
                                </div>
                            )
                        })}

                    {/* Agent Activity Cards (realtime SSE events) */}
                    {isGroupMode && activeAgents.map((agentName) => {
                        const agentColor = agentColorMap.get(agentName) || AGENT_COLORS[0];
                        const events = activityLog.filter(e => e.agentName === agentName);
                        const isThinking = events.length === 0 || events[events.length - 1].type === 'thinking';
                        return (
                            <div key={agentName} className="flex gap-6 p-8 border-b border-gray-100/50 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <Avatar className="h-8 w-8 mt-0.5 shrink-0 rounded-md">
                                    <AvatarFallback className={cn("text-[10px] flex items-center justify-center rounded-md font-medium", `${agentColor.bg} ${agentColor.text}`)}>
                                        {agentName.substring(0, 2).toUpperCase()}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex-1 min-w-0 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-muted-foreground">{agentName}</span>
                                    </div>
                                    {/* Step log */}
                                    <div className="space-y-1.5">
                                        {events.map((ev, i) => (
                                            <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                                                {ev.type === 'thinking' && (
                                                    <><Loader2 className="h-3.5 w-3.5 mt-0.5 shrink-0 animate-spin text-blue-500" /><span className="text-blue-500 font-medium">正在思考...</span></>
                                                )}
                                                {ev.type === 'tool_call' && (
                                                    <><Wrench className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-500" />
                                                        <span><span className="text-amber-600 font-medium">{ev.toolName}</span>{ev.args && <span className="text-gray-400 ml-1 font-mono text-[10px] break-all">{ev.args.length > 80 ? ev.args.slice(0, 80) + '…' : ev.args}</span>}</span></>
                                                )}
                                                {ev.type === 'tool_result' && (
                                                    <><CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-500" />
                                                        <span><span className="text-emerald-600 font-medium">{ev.toolName}</span><span className="text-gray-400 ml-1">{ev.result && ev.result.length > 80 ? ev.result.slice(0, 80) + '…' : ev.result}</span></span></>
                                                )}
                                                {ev.type === 'error' && (
                                                    <><AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-red-500" /><span className="text-red-500">{ev.result}</span></>
                                                )}
                                            </div>
                                        ))}
                                        {isThinking && events.length === 0 && (
                                            <div className="flex items-center gap-2 text-xs text-blue-500">
                                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                                <span className="font-medium">正在思考...</span>
                                            </div>
                                        )}
                                    </div>
                                    {/* Typing dots */}
                                    <div className="flex items-center gap-1 h-4">
                                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {isLoading && (
                        <div className="flex gap-4 p-6 border-b border-border/40">
                            <Avatar className="h-8 w-8 mt-1 shrink-0">
                                <AvatarFallback className="bg-blue-600 text-white text-xs">AI</AvatarFallback>
                            </Avatar>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                {isGroupMode ? "讨论中..." : t.sending}
                            </div>
                        </div>
                    )}
                    <div ref={scrollRef} />
                </div>
            </ScrollArea>



            {/* Input Area Container */}
            <div
                className={cn(
                    "absolute transition-all duration-500 ease-in-out z-20 px-4",
                    welcomeMode
                        ? "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl"
                        : "bottom-0 left-0 right-0 w-full bg-background/95 backdrop-blur pb-6 pt-4 border-t border-border/40"
                    // Style 01: Cleaner bottom area with subtle border
                )}
            >
                {/* Welcome Message */}
                <div
                    className={cn(
                        "text-center mb-8 transition-opacity duration-300",
                        welcomeMode ? "opacity-100" : "opacity-0 hidden"
                    )}
                >
                    {isGroupMode ? (
                        <>
                            <p className="text-xl text-muted-foreground font-light mt-8">
                                输入话题，让团队开始讨论
                            </p>
                        </>
                    ) : (
                        <>
                            <h1 className="text-4xl font-semibold bg-gradient-to-br from-gray-900 via-gray-700 to-gray-500 bg-clip-text text-transparent mb-3 tracking-tight">
                                {t.welcome.replace("{name}", displayName)}
                            </h1>
                            <p className="text-lg text-muted-foreground/80 font-light">
                                {t.welcomeSubtitle}
                            </p>
                        </>
                    )}
                </div>

                <div className={cn("w-full transition-all duration-500", !welcomeMode && "max-w-3xl mx-auto")}>
                    {/* Mode Switcher - Underlined Style */}
                    {isGroupMode && (
                        <div className="flex items-center gap-4 text-sm font-medium text-muted-foreground mb-2 pl-1 animate-in fade-in slide-in-from-bottom-1">
                            <button
                                onClick={() => setChatMode('workflow')}
                                className={cn(
                                    "hover:text-foreground transition-all pb-1 border-b-2",
                                    chatMode === 'workflow' ? "text-foreground border-foreground" : "border-transparent"
                                )}
                            >
                                工作流模式
                            </button>
                            <button
                                onClick={() => setChatMode('legacy')}
                                className={cn(
                                    "hover:text-foreground transition-all pb-1 border-b-2",
                                    chatMode === 'legacy' ? "text-foreground border-foreground" : "border-transparent"
                                )}
                            >
                                逐步模式
                            </button>
                        </div>
                    )}
                    <div className="relative group">
                        <div
                            className={cn(
                                "p-3 bg-background border rounded-xl relative z-20 shrink-0 shadow-sm transition-all focus-within:shadow-md",
                                isDragOver ? "border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/10" : "border-input focus-within:ring-1 focus-within:ring-ring/50"
                            )}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="max-w-3xl mx-auto relative flex gap-2 items-end">
                                <div className="flex-1 relative">
                                    {/* Mention Popup List */}
                                    {showMentionList && availableMembers.length > 0 && (
                                        <div className="absolute bottom-full left-0 mb-2 w-64 bg-popover border border-border rounded-md shadow-lg overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2">
                                            <div className="p-1">
                                                {availableMembers.map((agent, idx) => (
                                                    <button
                                                        key={agent.id}
                                                        onClick={() => insertMention(agent.name)}
                                                        className={cn(
                                                            "w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-sm transition-colors text-left",
                                                            idx === mentionIndex ? "bg-accent text-accent-foreground" : "hover:bg-muted"
                                                        )}
                                                    >
                                                        <Avatar className="h-5 w-5">
                                                            <AvatarFallback className="text-[10px]">
                                                                {agent.name[0]}
                                                            </AvatarFallback>
                                                        </Avatar>
                                                        <span>{agent.name}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Highlight Overlay */}
                                    <div
                                        aria-hidden="true"
                                        className="absolute inset-0 w-full px-0 py-0 text-lg leading-normal font-light bg-transparent whitespace-pre-wrap break-words pointer-events-none overflow-hidden"
                                        style={{
                                            minHeight: '24px',
                                            // Sync height with textarea
                                            height: textareaRef.current?.style.height || 'auto'
                                        }}
                                    >
                                        {/* Create a separate scrolling container to match textarea scroll */}
                                        <div
                                            ref={highlightRef}
                                            className="w-full h-full overflow-hidden"
                                        >
                                            {input.split(/(@[^\s]+|\[文件: [^\]]+\])/g).map((part, index) => {
                                                if (part.startsWith('@')) {
                                                    return <span key={index} className="text-blue-500 font-medium">{part}</span>
                                                } else if (part.startsWith('[文件: ')) {
                                                    const fileName = part.replace('[文件: ', '').replace(']', '').split('/').pop() || 'File'
                                                    return (
                                                        <span key={index} className="bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200 dark:border-blue-800 rounded-full px-2 py-0.5 text-sm font-medium inline-flex items-center gap-1.5 mx-0.5 pointer-events-auto align-baseline shadow-[0_1px_2px_rgba(59,130,246,0.1)] transition-transform hover:scale-105" title={part}>
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /></svg>
                                                            {fileName}
                                                        </span>
                                                    )
                                                }
                                                return <span key={index} className="text-foreground">{part}</span>
                                            })}
                                            {/* Add a zero-width space or break to ensure last line visibility if ends with newline */}
                                            {input.endsWith('\n') && <br />}
                                        </div>
                                    </div>

                                    <Textarea
                                        ref={textareaRef}
                                        placeholder={isGroupMode ? (chatMode === 'workflow' ? "输入目标，我来制定计划..." : "输入指令，一步步执行...") : t.placeholder}
                                        className="w-full relative z-10 border-0 focus:border-0 rounded-none px-0 py-0 resize-none shadow-none focus-visible:ring-0 outline-none focus:outline-none min-h-[24px] max-h-[200px] text-lg leading-normal font-light bg-transparent overflow-y-auto placeholder:text-muted-foreground/40 !ring-0 !ring-offset-0 text-transparent caret-foreground selection:bg-blue-100 selection:text-blue-900"
                                        value={input}
                                        onChange={handleInputChange}
                                        onKeyDown={handleKeyDown}
                                        disabled={isLoading || !hasTarget}
                                        autoFocus
                                        rows={1}
                                        style={{
                                            height: 'auto',
                                            minHeight: '24px',
                                            maxHeight: '200px'
                                        }}
                                        onInput={(e) => {
                                            const target = e.target as HTMLTextAreaElement
                                            target.style.height = 'auto'
                                            target.style.height = Math.min(target.scrollHeight, 200) + 'px'
                                            // Sync overlay
                                            if (highlightRef.current) {
                                                highlightRef.current.scrollTop = target.scrollTop;
                                            }
                                        }}
                                        onScroll={(e) => {
                                            if (highlightRef.current) {
                                                highlightRef.current.scrollTop = (e.target as HTMLElement).scrollTop
                                            }
                                        }}
                                    />
                                </div>
                                <input
                                    type="file"
                                    className="hidden"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    multiple
                                />
                                <Button
                                    variant="ghost" size="icon"
                                    className="h-8 w-8 shrink-0 rounded-full hover:bg-muted text-muted-foreground mb-0.5"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isUploading}
                                >
                                    {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-5 w-5" />}
                                </Button>
                            </div>
                        </div>

                        {/* Footer Text */}
                        <div className={cn("text-center mt-3 transition-opacity duration-500", welcomeMode ? "opacity-0" : "opacity-100")}>
                            <p className="text-[10px] text-muted-foreground/60">AI 可能会犯错，请核实重要信息。</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

// Message Content Component with Persona Mode Support
interface MessageContentProps {
    content: string
    role: string
    name?: string
    agents: any[]
    speakerName: string
    agentColor?: typeof AGENT_COLORS[0]
    isUser: boolean
    isGroupMode: boolean
    shouldAnimate?: boolean
}


function MessageContent({ content, role, name, agents, speakerName, isUser, shouldAnimate = false }: MessageContentProps) {

    // Get agent's persona mode
    const getAgentPersonaMode = () => {
        if (role !== 'assistant' || !name) return 'normal'
        const agent = agents.find(a => a.name === name)
        return agent?.persona_mode || 'normal'
    }

    const personaMode = getAgentPersonaMode()
    const parsed = parseMessage(content, personaMode)

    // Apply typewriter effect only if explicitly requested (new message)
    const triggerAnimation = shouldAnimate && !isUser
    const { displayedText } = useTypewriterEffect(
        triggerAnimation ? parsed.answer : "",
        10  // 10 characters at a time
    )

    const finalContent = triggerAnimation ? displayedText : parsed.answer

    return (
        <>
            {/* Style 01: Speaker Name Header */}
            <div className="flex items-center justify-between mb-1.5 h-6">
                <div className={cn(
                    "font-semibold text-sm flex items-center gap-2",
                    isUser ? "text-gray-900" : "text-gray-900" // Always dark/bold for names in Style 01
                )}>
                    {speakerName}
                    {name === 'Supervisor' && (
                        <span className="text-[10px] font-medium text-amber-600 bg-amber-50 border border-amber-100 px-1.5 py-0.5 rounded">
                            Supervisor
                        </span>
                    )}
                </div>

                {!isUser && (
                    <button
                        onClick={() => navigator.clipboard.writeText(finalContent)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded cursor-pointer"
                        title="Copy"
                    >
                        <Copy className="h-3 w-3 text-muted-foreground" />
                    </button>
                )}
            </div>

            {/* Style 01: Reasoning Section (Collapsible) */}
            {(parsed.reasoning || (parsed.mode === 'efficient' && parsed.reasoning)) && (
                <div className="mb-2">
                    <details className="group/thought">
                        <summary
                            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer w-fit select-none transition-colors"
                        >
                            <ChevronDown className="h-3 w-3 transition-transform -rotate-90 group-open/thought:rotate-0" />
                            Thinking Process
                        </summary>
                        <div className="mt-1.5 text-xs text-muted-foreground pl-3 border-l-2 border-border/40 space-y-1 font-mono">
                            {parsed.reasoning}
                        </div>
                    </details>
                </div>
            )}

            {/* Answer Content */}
            <div className="prose prose-sm dark:prose-invert max-w-none break-words text-[15px] leading-relaxed text-gray-800">
                <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                        code({ node, inline, className, children, ...props }: any) {
                            const match = /language-(\w+)/.exec(className || '')
                            return !inline && match ? (
                                <SyntaxHighlighter
                                    {...props}
                                    style={oneLight}
                                    language={match[1]}
                                    PreTag="div"
                                    customStyle={{ background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0', fontSize: '0.85rem', margin: '1em 0' }}
                                >
                                    {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                            ) : (
                                <code {...props} className={cn("bg-muted px-1 py-0.5 rounded font-mono text-sm", className)}>
                                    {children}
                                </code>
                            )
                        },
                        // Table styles
                        table({ children, ...props }: any) {
                            return (
                                <div className="overflow-x-auto my-4 rounded-lg border border-gray-200 shadow-sm">
                                    <table {...props} className="min-w-full text-sm">{children}</table>
                                </div>
                            )
                        },
                        thead({ children, ...props }: any) {
                            return <thead {...props} className="bg-gray-50 border-b border-gray-200">{children}</thead>
                        },
                        tbody({ children, ...props }: any) {
                            return <tbody {...props} className="divide-y divide-gray-100">{children}</tbody>
                        },
                        tr({ children, ...props }: any) {
                            return <tr {...props} className="hover:bg-gray-50/60 transition-colors">{children}</tr>
                        },
                        th({ children, ...props }: any) {
                            return <th {...props} className="px-4 py-2.5 text-left font-semibold text-gray-700 text-xs uppercase tracking-wide">{children}</th>
                        },
                        td({ children, ...props }: any) {
                            return <td {...props} className="px-4 py-2.5 text-gray-700 align-top">{children}</td>
                        },
                    }}
                >
                    {finalContent}
                </ReactMarkdown>
            </div>
        </>
    )
}

