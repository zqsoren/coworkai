import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Switch } from "@/components/ui/switch"
import { Plus, Trash2, Clock, CalendarDays, Timer, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchScheduledTasks, createScheduledTask, updateScheduledTask, deleteScheduledTask } from "@/lib/api"
import type { ScheduledTask } from "@/lib/api"

interface Props {
    open: boolean
    onOpenChange: (open: boolean) => void
    agentId: string
    workspaceId: string
}

const DOW_OPTIONS = [
    { value: "mon", label: "周一" },
    { value: "tue", label: "周二" },
    { value: "wed", label: "周三" },
    { value: "thu", label: "周四" },
    { value: "fri", label: "周五" },
    { value: "sat", label: "周六" },
    { value: "sun", label: "周日" },
]

const INTERVAL_UNIT_OPTIONS = [
    { value: "minutes", label: "分钟" },
    { value: "hours", label: "小时" },
    { value: "days", label: "天" },
    { value: "weeks", label: "周" },
]

/* Shared style for native <select> to match the design system */
const nativeSelectClass = "h-8 rounded-none text-xs border border-gray-300 dark:border-zinc-700 bg-transparent px-2 appearance-none cursor-pointer focus:outline-none focus:border-black dark:focus:border-white"

function taskSummary(t: ScheduledTask): string {
    if (t.mode === "calendar") {
        const prefix = t.scope === "every" ? "每" : "本"
        if (t.calendar_unit === "day") return `${prefix}日 ${t.time}`
        if (t.calendar_unit === "week") {
            const dow = DOW_OPTIONS.find(d => d.value === t.day_of_week)?.label || t.day_of_week
            return `${prefix}${dow} ${t.time}`
        }
        if (t.calendar_unit === "month") return `${prefix}月${t.day_of_month}号 ${t.time}`
    }
    if (t.mode === "interval") {
        const unit = INTERVAL_UNIT_OPTIONS.find(u => u.value === t.interval_unit)?.label || t.interval_unit
        return `${t.work_start}–${t.work_end} 每${t.interval_value}${unit}`
    }
    return "未知"
}

export { taskSummary }

export function ScheduleTaskPanel({ open, onOpenChange, agentId, workspaceId }: Props) {
    const [tasks, setTasks] = useState<ScheduledTask[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isCreating, setIsCreating] = useState(false)
    const [showForm, setShowForm] = useState(false)

    // Form state
    const [mode, setMode] = useState<"calendar" | "interval">("calendar")
    const [scope, setScope] = useState("every")
    const [calendarUnit, setCalendarUnit] = useState("day")
    const [time, setTime] = useState("09:00")
    const [dayOfWeek, setDayOfWeek] = useState("mon")
    const [dayOfMonth, setDayOfMonth] = useState(1)
    const [workStart, setWorkStart] = useState("09:00")
    const [workEnd, setWorkEnd] = useState("18:00")
    const [intervalValue, setIntervalValue] = useState(1)
    const [intervalUnit, setIntervalUnit] = useState("hours")
    const [prompt, setPrompt] = useState("")

    const loadTasks = async () => {
        setIsLoading(true)
        try {
            const data = await fetchScheduledTasks(agentId)
            setTasks(data)
        } catch (e) { console.error(e) }
        finally { setIsLoading(false) }
    }

    useEffect(() => {
        if (open && agentId) loadTasks()
    }, [open, agentId])

    const resetForm = () => {
        setMode("calendar")
        setScope("every")
        setCalendarUnit("day")
        setTime("09:00")
        setDayOfWeek("mon")
        setDayOfMonth(1)
        setWorkStart("09:00")
        setWorkEnd("18:00")
        setIntervalValue(1)
        setIntervalUnit("hours")
        setPrompt("")
        setShowForm(false)
    }

    const handleCreate = async () => {
        if (!prompt.trim()) return
        setIsCreating(true)
        try {
            await createScheduledTask({
                agent_id: agentId,
                workspace_id: workspaceId,
                mode,
                scope: mode === "calendar" ? scope : undefined,
                calendar_unit: mode === "calendar" ? calendarUnit : undefined,
                time: mode === "calendar" ? time : undefined,
                day_of_week: mode === "calendar" && calendarUnit === "week" ? dayOfWeek : undefined,
                day_of_month: mode === "calendar" && calendarUnit === "month" ? dayOfMonth : undefined,
                work_start: mode === "interval" ? workStart : undefined,
                work_end: mode === "interval" ? workEnd : undefined,
                interval_value: mode === "interval" ? intervalValue : undefined,
                interval_unit: mode === "interval" ? intervalUnit : undefined,
                prompt,
                enabled: true,
            })
            resetForm()
            await loadTasks()
        } catch (e) { console.error(e) }
        finally { setIsCreating(false) }
    }

    const handleToggle = async (taskId: string, enabled: boolean) => {
        try {
            await updateScheduledTask(taskId, { enabled })
            setTasks(prev => prev.map(t => t.id === taskId ? { ...t, enabled } : t))
        } catch (e) { console.error(e) }
    }

    const handleDelete = async (taskId: string) => {
        if (!confirm("确定删除该定时任务？")) return
        try {
            await deleteScheduledTask(taskId)
            setTasks(prev => prev.filter(t => t.id !== taskId))
        } catch (e) { console.error(e) }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[520px] max-h-[85vh] flex flex-col rounded-none border-gray-300 dark:border-zinc-700">
                <DialogHeader>
                    <DialogTitle className="text-base font-semibold flex items-center gap-2">
                        <Clock className="w-4 h-4" /> 定时任务
                    </DialogTitle>
                    <DialogDescription className="text-xs text-gray-500">
                        设定定时触发的提示词，系统将按时自动发送给智能体执行
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-hidden flex flex-col gap-4">
                    {/* Task List */}
                    <ScrollArea className="flex-1 min-h-0">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-10">
                                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                            </div>
                        ) : tasks.length === 0 && !showForm ? (
                            <div className="text-center text-gray-400 text-sm py-10 italic">
                                暂无定时任务
                            </div>
                        ) : (
                            <div className="space-y-2 pr-2">
                                {tasks.map(t => (
                                    <div
                                        key={t.id}
                                        className={cn(
                                            "border rounded-none p-3 space-y-1.5 transition-colors",
                                            t.enabled
                                                ? "border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-950"
                                                : "border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900 opacity-60"
                                        )}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                {t.mode === "calendar"
                                                    ? <CalendarDays className="w-3.5 h-3.5 text-blue-500" />
                                                    : <Timer className="w-3.5 h-3.5 text-orange-500" />
                                                }
                                                <span className="text-xs font-medium">{taskSummary(t)}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Switch
                                                    checked={t.enabled}
                                                    onCheckedChange={(v) => handleToggle(t.id, v)}
                                                    className="scale-75"
                                                />
                                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleDelete(t.id)}>
                                                    <Trash2 className="w-3 h-3 text-gray-400 hover:text-red-500" />
                                                </Button>
                                            </div>
                                        </div>
                                        <p className="text-[11px] text-gray-500 truncate pl-5" title={t.prompt}>
                                            {t.prompt}
                                        </p>
                                        {t.last_run && (
                                            <p className="text-[10px] text-gray-400 pl-5">
                                                上次: {new Date(t.last_run).toLocaleString("zh-CN")} · {t.last_status}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>

                    {/* Create Form */}
                    {showForm ? (
                        <div className="border border-gray-300 dark:border-zinc-700 p-4 space-y-4 bg-gray-50/50 dark:bg-zinc-900/50">
                            {/* Mode switcher */}
                            <div className="flex w-full border border-gray-300 dark:border-zinc-700">
                                <button
                                    type="button"
                                    className={cn(
                                        "flex-1 h-8 flex items-center justify-center gap-1.5 text-xs transition-colors",
                                        mode === "calendar"
                                            ? "bg-black text-white dark:bg-white dark:text-black"
                                            : "bg-transparent text-gray-500 hover:text-black dark:hover:text-white"
                                    )}
                                    onClick={() => setMode("calendar")}
                                >
                                    <CalendarDays className="w-3 h-3" /> 日历调度
                                </button>
                                <button
                                    type="button"
                                    className={cn(
                                        "flex-1 h-8 flex items-center justify-center gap-1.5 text-xs transition-colors",
                                        mode === "interval"
                                            ? "bg-black text-white dark:bg-white dark:text-black"
                                            : "bg-transparent text-gray-500 hover:text-black dark:hover:text-white"
                                    )}
                                    onClick={() => setMode("interval")}
                                >
                                    <Timer className="w-3 h-3" /> 工作循环
                                </button>
                            </div>

                            {/* Calendar mode — native selects */}
                            <div className={mode !== "calendar" ? "hidden" : "flex items-center gap-2 flex-wrap"}>
                                <select
                                    value={scope}
                                    onChange={e => setScope(e.target.value)}
                                    className={cn(nativeSelectClass, "w-16")}
                                >
                                    <option value="every">每</option>
                                    <option value="this">本</option>
                                </select>

                                <select
                                    value={calendarUnit}
                                    onChange={e => setCalendarUnit(e.target.value)}
                                    className={cn(nativeSelectClass, "w-16")}
                                >
                                    <option value="day">日</option>
                                    <option value="week">周</option>
                                    <option value="month">月</option>
                                </select>

                                {calendarUnit === "week" && (
                                    <select
                                        value={dayOfWeek}
                                        onChange={e => setDayOfWeek(e.target.value)}
                                        className={cn(nativeSelectClass, "w-20")}
                                    >
                                        {DOW_OPTIONS.map(d => (
                                            <option key={d.value} value={d.value}>{d.label}</option>
                                        ))}
                                    </select>
                                )}

                                {calendarUnit === "month" && (
                                    <select
                                        value={String(dayOfMonth)}
                                        onChange={e => setDayOfMonth(Number(e.target.value))}
                                        className={cn(nativeSelectClass, "w-20")}
                                    >
                                        {Array.from({ length: 31 }, (_, i) => i + 1).map(d => (
                                            <option key={d} value={String(d)}>{d}号</option>
                                        ))}
                                    </select>
                                )}

                                <Input
                                    type="time"
                                    value={time}
                                    onChange={e => setTime(e.target.value)}
                                    className="w-28 h-8 rounded-none text-xs border-gray-300 dark:border-zinc-700"
                                />
                            </div>

                            {/* Interval mode — native selects */}
                            <div className={mode !== "interval" ? "hidden" : "space-y-3"}>
                                <div className="flex items-center gap-2">
                                    <Label className="text-[10px] text-gray-500 shrink-0">时段</Label>
                                    <Input
                                        type="time"
                                        value={workStart}
                                        onChange={e => setWorkStart(e.target.value)}
                                        className="w-24 h-8 rounded-none text-xs border-gray-300 dark:border-zinc-700"
                                    />
                                    <span className="text-xs text-gray-400">—</span>
                                    <Input
                                        type="time"
                                        value={workEnd}
                                        onChange={e => setWorkEnd(e.target.value)}
                                        className="w-24 h-8 rounded-none text-xs border-gray-300 dark:border-zinc-700"
                                    />
                                </div>
                                <div className="flex items-center gap-2">
                                    <Label className="text-[10px] text-gray-500 shrink-0">每隔</Label>
                                    <Input
                                        type="number"
                                        min={1}
                                        value={intervalValue}
                                        onChange={e => setIntervalValue(Number(e.target.value) || 1)}
                                        className="w-16 h-8 rounded-none text-xs border-gray-300 dark:border-zinc-700"
                                    />
                                    <select
                                        value={intervalUnit}
                                        onChange={e => setIntervalUnit(e.target.value)}
                                        className={cn(nativeSelectClass, "w-20")}
                                    >
                                        {INTERVAL_UNIT_OPTIONS.map(u => (
                                            <option key={u.value} value={u.value}>{u.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Prompt */}
                            <div className="space-y-1.5">
                                <Label className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">触发提示词</Label>
                                <Textarea
                                    value={prompt}
                                    onChange={e => setPrompt(e.target.value)}
                                    placeholder="到时间时自动发送给智能体的消息..."
                                    className="min-h-[80px] text-xs resize-y rounded-none border-gray-300 dark:border-zinc-700 bg-transparent"
                                />
                            </div>

                            {/* Actions */}
                            <div className="flex justify-end gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="rounded-none text-xs border-gray-300 dark:border-zinc-700"
                                    onClick={resetForm}
                                >
                                    取消
                                </Button>
                                <Button
                                    size="sm"
                                    className="rounded-none text-xs bg-black text-white hover:bg-zinc-800 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
                                    onClick={handleCreate}
                                    disabled={isCreating || !prompt.trim()}
                                >
                                    {isCreating ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                                    保存任务
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <Button
                            variant="outline"
                            className="w-full rounded-none border-dashed border-gray-300 dark:border-zinc-700 text-xs text-gray-500 hover:text-black dark:hover:text-white"
                            onClick={() => setShowForm(true)}
                        >
                            <Plus className="w-3.5 h-3.5 mr-1.5" /> 新建定时任务
                        </Button>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}
