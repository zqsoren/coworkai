import { useState, useEffect, useRef } from "react"
import { Feather, X, Zap, Info, Check, Copy } from "lucide-react"
import { cn } from "@/lib/utils"
import { useStore } from "@/store"
import { summarizeBasket, testConnectivity } from "@/lib/api"

const STORAGE_KEY = "agentos_basket"

interface BasketItem {
    id: string
    text: string
    savedAt: string
}

function load(): BasketItem[] {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]")
    } catch {
        return []
    }
}

function save(items: BasketItem[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export function Basket() {
    const { addMessage } = useStore()
    const [items, setItems] = useState<BasketItem[]>(load)
    const [isOpen, setIsOpen] = useState(false)
    const [isDragOver, setIsDragOver] = useState(false)
    const [isGlobalDragging, setIsGlobalDragging] = useState(false)
    const [justDropped, setJustDropped] = useState(false)
    const [isSummarizing, setIsSummarizing] = useState(false)
    const [copySuccess, setCopySuccess] = useState<string | null>(null)
    const [connStatus, setConnStatus] = useState<'idle' | 'ok' | 'fail'>('idle')
    const [customInstruction, setCustomInstruction] = useState('')
    const dragCountRef = useRef(0)

    useEffect(() => {
        const onDragStart = () => {
            dragCountRef.current += 1
            setIsGlobalDragging(true)
        }
        const onDragEnd = () => {
            dragCountRef.current = Math.max(0, dragCountRef.current - 1)
            if (dragCountRef.current === 0) setIsGlobalDragging(false)
        }
        document.addEventListener("dragstart", onDragStart)
        document.addEventListener("dragend", onDragEnd)
        return () => {
            document.removeEventListener("dragstart", onDragStart)
            document.removeEventListener("dragend", onDragEnd)
        }
    }, [])

    useEffect(() => {
        if (isOpen && connStatus === 'idle') {
            testConnectivity().then(ok => setConnStatus(ok ? 'ok' : 'fail'))
        }
    }, [isOpen, connStatus])

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = "copy"
        setIsDragOver(true)
    }

    const handleDragLeave = () => setIsDragOver(false)

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragOver(false)
        setIsGlobalDragging(false)

        const text = e.dataTransfer.getData("text/plain").trim()
        if (!text) return

        const newItem: BasketItem = {
            id: `basket_${Date.now()}`,
            text,
            savedAt: new Date().toISOString()
        }

        setItems(prev => {
            if (prev.some(i => i.text === text)) return prev
            const next = [newItem, ...prev]
            save(next)
            return next
        })

        setJustDropped(true)
        setTimeout(() => setJustDropped(false), 800)
        setIsOpen(true)
    }

    const removeItem = (id: string) => {
        setItems(prev => {
            const next = prev.filter(i => i.id !== id)
            save(next)
            return next
        })
    }

    const copyItem = (id: string, text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            setCopySuccess(id)
            setTimeout(() => setCopySuccess(null), 2000)
        }).catch(() => { })
    }

    const copyAll = () => {
        const combined = items.map((item, i) => `${i + 1}. ${item.text}`).join("\n\n")
        navigator.clipboard.writeText(combined).catch(() => { })
    }

    const handleSummarize = async () => {
        if (items.length === 0 || isSummarizing) return
        const ok = await testConnectivity()
        if (!ok) {
            setConnStatus('fail')
            return
        }
        setConnStatus('ok')
        setIsSummarizing(true)
        try {
            const fragments = items.map(i => i.text)
            const state = useStore.getState()
            const summary = await summarizeBasket(
                fragments,
                state.currentWorkspaceId || undefined,
                state.currentGroupId || undefined,
                state.currentAgentId || undefined,
                customInstruction.trim() || undefined
            )

            const messageObj = { role: 'assistant' as const, content: summary, shouldAnimate: true, is_basket_summary: true }
            if (state.currentGroupId) {
                const key = state.currentGroupId
                const updatedMessages = [...(state.groupMessages[key] || []), messageObj]
                useStore.setState({ groupMessages: { ...state.groupMessages, [key]: updatedMessages as any } })
            } else {
                addMessage(messageObj as any)
            }
        } catch (error) {
            alert("汇总失败，请检查服务状态")
        } finally {
            setIsSummarizing(false)
        }
    }

    return (
        <div className="fixed bottom-8 right-8 z-[100] flex flex-col items-end gap-4 pointer-events-none">

            {/* Main Panel */}
            {isOpen && (
                <div className="pointer-events-auto w-[400px] bg-white border border-slate-100 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.12)] flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 duration-500 rounded-3xl">

                    {/* Header */}
                    <div className="px-8 pt-6 pb-4 flex justify-between items-center border-b border-slate-50/50">
                        <div className="flex items-center gap-2">
                            <span className="text-xl font-black text-slate-900 tracking-tighter">文本篮子</span>
                            {items.length > 0 && <span className="text-[10px] font-mono p-1 bg-slate-50 text-slate-400 rounded">0{items.length}</span>}
                        </div>
                        <div className="flex items-center gap-3">
                            {items.length > 0 && (
                                <button
                                    onClick={copyAll}
                                    className="text-[10px] font-bold uppercase tracking-widest text-slate-400 hover:text-blue-500 transition-colors flex items-center gap-1 px-2 py-1 rounded bg-slate-50 hover:bg-blue-50"
                                >
                                    <Copy className="w-3 h-3" /> 复制全部
                                </button>
                            )}
                            <button
                                onClick={() => setIsOpen(false)}
                                className="p-1.5 rounded-full hover:bg-slate-100 text-slate-300 hover:text-slate-900 transition-all"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto px-8 max-h-[400px] custom-scrollbar">
                        {items.length === 0 ? (
                            <div className="py-20 flex flex-col items-center justify-center text-center opacity-20">
                                <Feather className="w-12 h-12 mb-4" />
                                <p className="text-xs font-black uppercase tracking-widest">可以将琐碎的文字拖拽至此，整理汇总</p>
                            </div>
                        ) : (
                            <div className="space-y-12 pb-8">
                                {items.map((item) => (
                                    <div key={item.id} className="group space-y-4">
                                        <p className="text-[11px] text-slate-400 font-medium leading-relaxed group-hover:text-slate-900 transition-colors">
                                            {item.text}
                                        </p>
                                        <div className="flex justify-between items-center opacity-0 group-hover:opacity-100 transition-opacity">
                                            <span className="text-[9px] font-mono text-slate-200 uppercase">Stored: {new Date(item.savedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                            <div className="flex gap-4">
                                                <button
                                                    onClick={() => copyItem(item.id, item.text)}
                                                    className="text-[10px] font-black uppercase tracking-widest text-slate-300 hover:text-blue-500 flex items-center gap-1"
                                                >
                                                    {copySuccess === item.id ? <Check className="w-3 h-3" /> : "复制"}
                                                </button>
                                                <button
                                                    onClick={() => removeItem(item.id)}
                                                    className="text-[10px] font-black uppercase tracking-widest text-slate-300 hover:text-red-500"
                                                >
                                                    删除
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer / Actions */}
                    {items.length > 0 && (
                        <div className="p-8 pt-0 mt-auto space-y-3">
                            {/* Custom Instruction Input */}
                            <div className="relative">
                                <textarea
                                    value={customInstruction}
                                    onChange={e => setCustomInstruction(e.target.value)}
                                    placeholder="自定义指令（可选）：如「整理成表格」「写成一篇帖子」..."
                                    rows={2}
                                    className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-[11px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-slate-400 focus:bg-white transition-all"
                                />
                            </div>
                            <button
                                onClick={handleSummarize}
                                disabled={isSummarizing}
                                className={cn(
                                    "w-full rounded-2xl py-4 text-xs font-black uppercase tracking-widest transition-all flex items-center justify-center gap-3",
                                    isSummarizing ? "bg-slate-50 text-slate-300 cursor-wait" : "bg-slate-200 text-slate-800 hover:bg-slate-900 hover:text-white"
                                )}
                            >
                                {isSummarizing ? (
                                    <>
                                        <div className="w-2 h-2 bg-slate-400 animate-pulse rounded-full"></div>
                                        正在汇总...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-4 h-4" />
                                        一键汇总
                                    </>
                                )}
                            </button>
                            {connStatus === 'fail' && (
                                <p className="mt-4 text-[9px] text-red-400 font-bold uppercase text-center flex items-center justify-center gap-1">
                                    <Info className="w-3 h-3" /> Backend disconnected
                                </p>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Floating Trigger Button */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => setIsOpen(prev => !prev)}
                className={cn(
                    "pointer-events-auto relative flex items-center justify-center rounded-full cursor-pointer transition-all duration-700 select-none",
                    isGlobalDragging ? "w-20 h-20 shadow-2xl" : "w-14 h-14 shadow-[0_8px_30px_rgb(0,0,0,0.06)]",
                    isDragOver
                        ? "bg-slate-900 text-white scale-110 rotate-12"
                        : justDropped
                            ? "bg-green-500 text-white"
                            : isGlobalDragging
                                ? "bg-white border-2 border-dashed border-slate-200 text-slate-300 animate-pulse"
                                : "bg-white border border-slate-100 text-slate-300 hover:text-slate-900"
                )}
            >
                <Feather className={cn("transition-all", isGlobalDragging ? "w-8 h-8" : "w-6 h-6")} />

                {items.length > 0 && !isGlobalDragging && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-slate-900 text-white text-[9px] font-black rounded-full flex items-center justify-center tracking-tighter shadow-xl">
                        {items.length}
                    </span>
                )}

                {isGlobalDragging && !isDragOver && (
                    <span className="absolute -top-12 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] font-black px-3 py-1.5 rounded-full shadow-2xl animate-bounce">
                        STORE HERE
                    </span>
                )}
            </div>
        </div>
    )
}
