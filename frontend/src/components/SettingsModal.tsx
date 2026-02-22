import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Settings, Trash2, Save, Plus, Edit2, X, Check, Lock, ChevronsUpDown } from "lucide-react"
import { useStore } from "@/store"
import { translations } from "@/lib/i18n"
import type { OutputMode } from "@/lib/api"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { cn } from "@/lib/utils"

const PREDEFINED_PROVIDERS = [
    {
        id: "deepseek",
        name: "DeepSeek (深度求索)",
        type: "openai_compatible",
        defaultBaseUrl: "https://api.deepseek.com/v1",
        defaultKeyEnv: "DEEPSEEK_API_KEY",
        models: ["deepseek-chat", "deepseek-reasoner"]
    },
    {
        id: "gemini",
        name: "Google (Gemini)",
        type: "gemini",
        defaultBaseUrl: "",
        defaultKeyEnv: "GEMINI_API_KEY",
        models: ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-3-pro-preview"]
    },
    {
        id: "openai",
        name: "OpenAI",
        type: "openai",
        defaultBaseUrl: "https://api.openai.com/v1",
        defaultKeyEnv: "OPENAI_API_KEY",
        models: ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4.1-mini", "gpt-4"]
    },
    {
        id: "anthropic",
        name: "Anthropic (Claude)",
        type: "anthropic",
        defaultBaseUrl: "https://api.anthropic.com/v1",
        defaultKeyEnv: "ANTHROPIC_API_KEY",
        models: ["claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"]
    },
    {
        id: "minimax",
        name: "MiniMax",
        type: "openai_compatible",
        defaultBaseUrl: "https://api.minimax.chat/v1",
        defaultKeyEnv: "MINIMAX_API_KEY",
        models: ["MiniMax-M2.5"]
    },
    {
        id: "zhipu",
        name: "智谱清言 (ZhipuAI)",
        type: "openai_compatible",
        defaultBaseUrl: "https://open.bigmodel.cn/api/paas/v4",
        defaultKeyEnv: "ZHIPU_API_KEY",
        models: ["glm-5", "GLM-4.7", "GLM-4.7-FlashX"]
    },
    {
        id: "qwen",
        name: "通义千问 (Qwen)",
        type: "openai_compatible",
        defaultBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        defaultKeyEnv: "DASHSCOPE_API_KEY",
        models: ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"]
    },
    {
        id: "ernie",
        name: "文心一言 (Ernie)",
        type: "openai_compatible",
        defaultBaseUrl: "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        defaultKeyEnv: "QIANFAN_API_KEY",
        models: ["ernie-4.0-8k-latest", "ernie-3.5-8k", "ernie-speed-128k"]
    }
]

export function SettingsModal() {
    const { language } = useStore()
    const t = translations[language].settingsModal

    const [open, setOpen] = useState(false)
    const [providers, setProviders] = useState<any[]>([])

    // New Provider State
    const [selectedPredefinedId, setSelectedPredefinedId] = useState<string>("deepseek")
    const [newName, setNewName] = useState("DeepSeek")
    const [newBaseUrl, setNewBaseUrl] = useState("https://api.deepseek.com/v1")
    const [newKeyEnv, setNewKeyEnv] = useState("DEEPSEEK_API_KEY")
    const [newModel, setNewModel] = useState("deepseek-chat")

    // Combobox state
    const [modelComboboxOpen, setModelComboboxOpen] = useState(false)
    const [modelSearch, setModelSearch] = useState("")

    // Handle predefined provider change
    const handlePredefinedChange = (id: string) => {
        const pref = PREDEFINED_PROVIDERS.find(p => p.id === id)
        if (pref) {
            setSelectedPredefinedId(pref.id)
            setNewName(pref.name.split(" (")[0]) // clean name e.g. DeepSeek
            setNewBaseUrl(pref.defaultBaseUrl)
            setNewKeyEnv(pref.defaultKeyEnv)
            setNewModel(pref.models[0] || "")
            setModelSearch("")
        }
    }

    // Output Modes State
    const [outputModes, setOutputModes] = useState<OutputMode[]>([])
    const [editingModeId, setEditingModeId] = useState<string | null>(null)
    const [editName, setEditName] = useState("")
    const [editDescription, setEditDescription] = useState("")
    const [editPrompt, setEditPrompt] = useState("")

    // New Mode Form
    const [showAddMode, setShowAddMode] = useState(false)
    const [newModeName, setNewModeName] = useState("")
    const [newModeDescription, setNewModeDescription] = useState("")
    const [newModePrompt, setNewModePrompt] = useState("")

    useEffect(() => {
        if (open) {
            loadProviders()
            loadOutputModes()
        }
    }, [open])

    const loadProviders = async () => {
        const { fetchProviders: apiFetch } = await import("@/lib/api")
        const data = await apiFetch()
        setProviders(data)
    }

    const loadOutputModes = async () => {
        const { fetchOutputModes } = await import("@/lib/api")
        const data = await fetchOutputModes()
        setOutputModes(data)
    }

    const handleSave = async () => {
        if (!newName || !newModel) return
        const { saveProvider: apiSave } = await import("@/lib/api")
        const pref = PREDEFINED_PROVIDERS.find(p => p.id === selectedPredefinedId)

        // Generate a random ID behind the scenes
        const generatedId = `${selectedPredefinedId}_${Date.now()}`

        await apiSave({
            id: generatedId,
            type: pref ? pref.type : "openai_compatible",
            name: newName,
            models: [newModel], // Store the selected model
            base_url: newBaseUrl || undefined,
            api_key_env: newKeyEnv
        })

        loadProviders()
    }

    const handleDelete = async (id: string) => {
        const { deleteProvider: apiDelete } = await import("@/lib/api")
        await apiDelete(id)
        loadProviders()
    }

    // --- Output Mode Handlers ---
    const startEditMode = (mode: OutputMode) => {
        setEditingModeId(mode.id)
        setEditName(mode.name)
        setEditDescription(mode.description || "")
        setEditPrompt(mode.prompt || "")
    }

    const cancelEdit = () => {
        setEditingModeId(null)
    }

    const saveEditMode = async () => {
        if (!editingModeId) return
        const { updateOutputMode } = await import("@/lib/api")
        const mode = outputModes.find(m => m.id === editingModeId)
        const updates: any = { description: editDescription, prompt: editPrompt }
        // Only non-builtin can change name
        if (!mode?.is_builtin) updates.name = editName
        try {
            await updateOutputMode(editingModeId, updates)
            setEditingModeId(null)
            loadOutputModes()
        } catch (e: any) {
            alert(e?.response?.data?.detail || "更新失败")
        }
    }

    const handleDeleteMode = async (id: string) => {
        if (!confirm("确定要删除这个输出模式吗？")) return
        const { deleteOutputMode } = await import("@/lib/api")
        try {
            await deleteOutputMode(id)
            loadOutputModes()
        } catch (e: any) {
            alert(e?.response?.data?.detail || "删除失败")
        }
    }

    const handleCreateMode = async () => {
        if (!newModeName.trim() || !newModePrompt.trim()) {
            alert("模式名称和提示词不能为空")
            return
        }
        const { createOutputMode } = await import("@/lib/api")
        try {
            await createOutputMode({
                name: newModeName.trim(),
                description: newModeDescription.trim(),
                prompt: newModePrompt.trim()
            })
            setNewModeName("")
            setNewModeDescription("")
            setNewModePrompt("")
            setShowAddMode(false)
            loadOutputModes()
        } catch (e: any) {
            alert(e?.response?.data?.detail || "创建失败")
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" title={t.title}>
                    <Settings className="w-4 h-4 text-muted-foreground" />
                </Button>
            </DialogTrigger>
            <DialogContent className="w-[95vw] max-w-3xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{t.title}</DialogTitle>
                </DialogHeader>

                <div className="space-y-8 py-4">

                    {/* ─── LLM Providers ─── */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-foreground">AI大模型配置</h3>
                        <div className="space-y-2">
                            {/* Builtin (Free) providers */}
                            {providers.filter(p => p.is_builtin).length > 0 && (
                                <div className="space-y-2 mb-3">
                                    <div className="flex items-center gap-2 text-xs font-semibold text-green-600 dark:text-green-400">
                                        <Lock className="h-3 w-3" />
                                        <span>系统内置</span>
                                    </div>
                                    {providers.filter(p => p.is_builtin).map(p => (
                                        <div key={p.id} className="flex items-center justify-between p-3 border border-green-200 dark:border-green-900 rounded-md bg-green-50/50 dark:bg-green-950/20">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="font-semibold text-sm">{p.name}</span>
                                                    <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700">
                                                        FREE
                                                    </span>
                                                </div>
                                            </div>
                                            <Lock className="h-4 w-4 text-green-500 opacity-50" />
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* User-defined providers */}
                            {providers.filter(p => !p.is_builtin).map(p => (
                                <div key={p.id} className="flex items-center justify-between p-3 border rounded-md bg-muted/20">
                                    <div>
                                        <div className="font-semibold text-sm">{p.name} <span className="text-xs text-muted-foreground">({p.type})</span></div>
                                        <div className="text-xs text-muted-foreground">{p.base_url || "Default URL"}</div>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={() => handleDelete(p.id)}>
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                    </Button>
                                </div>
                            ))}
                            {providers.length === 0 && <div className="text-sm text-muted-foreground">{t.noProviders}</div>}
                        </div>

                        <div className="border-t pt-4">
                            <h4 className="text-sm font-medium mb-3">添加大模型配置</h4>
                            <div className="grid gap-3 p-4 bg-muted/30 border rounded-lg">
                                {/* Row 1: Provider selection & Custom Name */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-semibold">1. 选择大模型供应商</Label>
                                        <Select value={selectedPredefinedId} onValueChange={handlePredefinedChange}>
                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                {PREDEFINED_PROVIDERS.map(p => (
                                                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-semibold">配置名称 (用于区分)</Label>
                                        <Input value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. My DeepSeek" />
                                    </div>
                                </div>

                                {/* Row 2: Model Combobox */}
                                <div className="space-y-1.5 mt-1">
                                    <Label className="text-xs font-semibold">2. 默认模型型号</Label>
                                    <Popover open={modelComboboxOpen} onOpenChange={setModelComboboxOpen}>
                                        <PopoverTrigger asChild>
                                            <Button
                                                variant="outline"
                                                role="combobox"
                                                aria-expanded={modelComboboxOpen}
                                                className="w-full justify-between font-normal bg-background"
                                            >
                                                {newModel || "Select or type a model..."}
                                                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                                            <Command>
                                                <CommandInput
                                                    placeholder="Search or type a new model..."
                                                    value={modelSearch}
                                                    onValueChange={setModelSearch}
                                                />
                                                <CommandList>
                                                    <CommandEmpty className="p-2 text-center text-sm">
                                                        找不到预设?
                                                        <Button
                                                            variant="secondary"
                                                            size="sm"
                                                            className="w-full mt-2"
                                                            onClick={() => {
                                                                setNewModel(modelSearch)
                                                                setModelComboboxOpen(false)
                                                            }}
                                                        >
                                                            使用自定义: {modelSearch}
                                                        </Button>
                                                    </CommandEmpty>
                                                    <CommandGroup heading="预设推荐模型">
                                                        {PREDEFINED_PROVIDERS.find(p => p.id === selectedPredefinedId)?.models.map((model) => (
                                                            <CommandItem
                                                                key={model}
                                                                value={model}
                                                                onSelect={(currentValue: string) => {
                                                                    setNewModel(currentValue)
                                                                    setModelSearch("")
                                                                    setModelComboboxOpen(false)
                                                                }}
                                                            >
                                                                <Check
                                                                    className={cn(
                                                                        "mr-2 h-4 w-4",
                                                                        newModel === model ? "opacity-100" : "opacity-0"
                                                                    )}
                                                                />
                                                                {model}
                                                            </CommandItem>
                                                        ))}
                                                    </CommandGroup>
                                                </CommandList>
                                            </Command>
                                        </PopoverContent>
                                    </Popover>
                                </div>

                                {/* Row 3: API Connection Details */}
                                <div className="grid grid-cols-[2fr_1fr] gap-3 mt-1">
                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-semibold text-muted-foreground">Base URL</Label>
                                        <Input value={newBaseUrl} onChange={e => setNewBaseUrl(e.target.value)} placeholder="https://..." className="bg-background text-sm" />
                                    </div>
                                    <div className="space-y-1.5">
                                        <Label className="text-xs font-semibold text-muted-foreground">API密钥</Label>
                                        <Input value={newKeyEnv} onChange={e => setNewKeyEnv(e.target.value)} placeholder="API_KEY_ENV" className="bg-background text-sm" />
                                    </div>
                                </div>

                                <Button onClick={handleSave} className="w-full mt-2" disabled={!newName || !newModel}>
                                    <Save className="mr-2 h-4 w-4" /> 添加该配置
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* ─── Output Modes ─── */}
                    <div className="space-y-3 border-t pt-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-foreground">智能体输出模式管理</h3>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => { setShowAddMode(!showAddMode); setEditingModeId(null) }}
                            >
                                {showAddMode ? <X className="h-3.5 w-3.5 mr-1" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
                                {showAddMode ? "取消" : "新增模式"}
                            </Button>
                        </div>

                        <p className="text-xs text-muted-foreground">
                            可新增自定义输出模式，并为每个智能体单独选择。内建模式不可删除，但可修改提示词。
                        </p>

                        {/* Mode List */}
                        <div className="space-y-2">
                            {outputModes.map(mode => (
                                <div key={mode.id} className="border rounded-lg overflow-hidden">
                                    {editingModeId === mode.id ? (
                                        /* Edit Form */
                                        <div className="p-3 space-y-3 bg-muted/20">
                                            <div className="flex items-center gap-2">
                                                {mode.is_builtin ? (
                                                    <div className="flex-1 font-medium text-sm flex items-center gap-1.5">
                                                        <Lock className="h-3 w-3 text-muted-foreground" />
                                                        {mode.name}
                                                        <span className="text-xs text-muted-foreground font-normal">(内建，名称不可改)</span>
                                                    </div>
                                                ) : (
                                                    <Input
                                                        value={editName}
                                                        onChange={e => setEditName(e.target.value)}
                                                        className="flex-1 h-8 text-sm font-medium"
                                                        placeholder="模式名称"
                                                    />
                                                )}
                                                <Button size="sm" onClick={saveEditMode} className="h-8 px-2.5">
                                                    <Check className="h-3.5 w-3.5 mr-1" /> 保存
                                                </Button>
                                                <Button size="sm" variant="ghost" onClick={cancelEdit} className="h-8 px-2">
                                                    <X className="h-3.5 w-3.5" />
                                                </Button>
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs">描述</Label>
                                                <Input
                                                    value={editDescription}
                                                    onChange={e => setEditDescription(e.target.value)}
                                                    className="h-8 text-sm"
                                                    placeholder="简短描述"
                                                />
                                            </div>
                                            <div className="space-y-1">
                                                <Label className="text-xs">提示词（追加到系统 Prompt 后面）</Label>
                                                <Textarea
                                                    value={editPrompt}
                                                    onChange={e => setEditPrompt(e.target.value)}
                                                    className="h-28 text-sm font-mono resize-none"
                                                    placeholder="输入此模式的提示词..."
                                                />
                                            </div>
                                        </div>
                                    ) : (
                                        /* Display Row */
                                        <div className="flex items-start justify-between p-3 hover:bg-muted/20 transition-colors">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-1.5">
                                                    {mode.is_builtin && <Lock className="h-3 w-3 text-muted-foreground shrink-0" />}
                                                    <span className="font-medium text-sm truncate">{mode.name}</span>
                                                </div>
                                                {mode.description && (
                                                    <p className="text-xs text-muted-foreground mt-0.5">{mode.description}</p>
                                                )}
                                                {mode.prompt && (
                                                    <p className="text-xs text-muted-foreground/60 mt-1 truncate font-mono">{mode.prompt.slice(0, 60)}...</p>
                                                )}
                                                {!mode.prompt && (
                                                    <p className="text-xs text-muted-foreground/50 mt-1 italic">无额外提示词</p>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-1 ml-2 shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-7 w-7"
                                                    onClick={() => startEditMode(mode)}
                                                    title="编辑"
                                                >
                                                    <Edit2 className="h-3.5 w-3.5" />
                                                </Button>
                                                {!mode.is_builtin && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-7 w-7 text-destructive hover:text-destructive"
                                                        onClick={() => handleDeleteMode(mode.id)}
                                                        title="删除"
                                                    >
                                                        <Trash2 className="h-3.5 w-3.5" />
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Add New Mode Form */}
                        {showAddMode && (
                            <div className="border rounded-lg p-4 space-y-3 bg-blue-50/50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
                                <h4 className="text-sm font-medium text-blue-700 dark:text-blue-400">新建输出模式</h4>
                                <div className="space-y-1">
                                    <Label className="text-xs">模式名称 *</Label>
                                    <Input
                                        value={newModeName}
                                        onChange={e => setNewModeName(e.target.value)}
                                        placeholder="e.g. 学术写作模式"
                                        className="h-8 text-sm"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">描述</Label>
                                    <Input
                                        value={newModeDescription}
                                        onChange={e => setNewModeDescription(e.target.value)}
                                        placeholder="简短说明这个模式的用途"
                                        className="h-8 text-sm"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">提示词 *（会追加到系统 Prompt 后面）</Label>
                                    <Textarea
                                        value={newModePrompt}
                                        onChange={e => setNewModePrompt(e.target.value)}
                                        placeholder="请以学术论文的格式和语气进行回答..."
                                        className="h-28 text-sm font-mono resize-none"
                                    />
                                </div>
                                <Button onClick={handleCreateMode} className="w-full" size="sm">
                                    <Plus className="h-3.5 w-3.5 mr-1.5" /> 创建模式
                                </Button>
                            </div>
                        )}
                    </div>

                </div>
            </DialogContent>
        </Dialog>
    )
}
