import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Send, Zap, ArrowUp, ArrowRight, Sparkles, Layers } from "lucide-react"
import { cn } from "@/lib/utils"

export function ChatInputShowcase() {

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center py-16 px-4 font-sans">
            <div className="max-w-5xl w-full space-y-16">
                <div className="text-center space-y-4">
                    <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
                        Light & Interactive Inputs
                    </h1>
                    <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                        10 distinct light-themed designs. Click the mode toggle to see the interaction state.
                    </p>
                </div>

                <div className="grid gap-16">
                    {/* Style 1: Soft Shadow Pills */}
                    <StyleSection title="1. Soft Shadow Pill" description="Pure white, floating, gentle shadows.">
                        <InputDemo1 />
                    </StyleSection>

                    {/* Style 2: Borderless Minimal */}
                    <StyleSection title="2. Borderless Minimal" description="Focus on content, subtle interactions.">
                        <InputDemo2 />
                    </StyleSection>

                    {/* Style 3: Split Action Bar */}
                    <StyleSection title="3. Split Action Bar" description="Separates input from controls clearly.">
                        <InputDemo3 />
                    </StyleSection>

                    {/* Style 4: iOS Frosted Glass */}
                    <StyleSection title="4. Frosted Glass" description="Translucent background, blur effect.">
                        <InputDemo4 />
                    </StyleSection>

                    {/* Style 5: Integrated Badge */}
                    <StyleSection title="5. Integrated Badge" description="Mode switch inside the input field.">
                        <InputDemo5 />
                    </StyleSection>

                    {/* Style 6: Material You Soft */}
                    <StyleSection title="6. Material Soft" description="Relaxed rounded corners, pastel hover.">
                        <InputDemo6 />
                    </StyleSection>

                    {/* Style 7: Underlined Clean */}
                    <StyleSection title="7. Underlined Clean" description="Classic text field with modern twist.">
                        <InputDemo7 />
                    </StyleSection>

                    {/* Style 8: Boxy Tech Light */}
                    <StyleSection title="8. Boxy Tech Light" description="Square corners, precise hairlines.">
                        <InputDemo8 />
                    </StyleSection>

                    {/* Style 9: Floating Action Button */}
                    <StyleSection title="9. FAB Style" description="Prominent send button, airy input.">
                        <InputDemo9 />
                    </StyleSection>

                    {/* Style 10: Dynamic Notch */}
                    <StyleSection title="10. Dynamic Notch" description="Input expands from a central pill.">
                        <InputDemo10 />
                    </StyleSection>
                </div>
            </div>
        </div>
    )
}

function StyleSection({ title, description, children }: { title: string, description: string, children: React.ReactNode }) {
    return (
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
            <div className="mb-6 pb-4 border-b border-gray-100">
                <h2 className="text-xl font-bold text-gray-800">{title}</h2>
                <p className="text-gray-500 text-sm mt-1">{description}</p>
            </div>
            {children}
        </div>
    )
}

// --- Individual Demos to manage state independently ---

function InputDemo1() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-gray-50/50 p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl relative group">
                <div className="absolute left-2 bottom-3 z-10">
                    <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-200/50 transition-colors">
                        <Plus className="h-5 w-5" />
                    </Button>
                </div>
                <Textarea
                    placeholder="Ask anything..."
                    className="w-full bg-white min-h-[56px] py-4 pl-12 pr-32 rounded-[28px] border-none shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] focus-visible:ring-0 resize-none text-base placeholder:text-gray-400 text-gray-700"
                />
                <div className="absolute right-2 bottom-2 bg-gray-50 p-1 rounded-[24px] flex items-center gap-1 border border-gray-100">
                    <button
                        onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-white shadow-sm border border-gray-100 hover:bg-gray-50 transition-all text-gray-600 active:scale-95"
                    >
                        {mode === 'workflow' ? <Zap className="h-3 w-3 text-amber-500 fill-amber-500" /> : <Layers className="h-3 w-3 text-blue-500" />}
                        {mode === 'workflow' ? 'Workflow' : 'Step-by-Step'}
                    </button>
                    <Button size="icon" className="h-8 w-8 rounded-full bg-gray-900 text-white shadow-md hover:bg-gray-800">
                        <ArrowUp className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    )
}

function InputDemo2() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-white p-10 rounded-2xl border flex justify-center">
            <div className="w-full max-w-2xl border-b border-gray-200 focus-within:border-blue-500 transition-colors relative">
                <Textarea
                    placeholder="Type a message..."
                    className="w-full border-none shadow-none focus-visible:ring-0 resize-none px-0 py-3 text-lg min-h-[50px] placeholder:text-gray-300"
                />
                <div className="flex justify-between items-center py-2">
                    <div className="flex gap-2">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-blue-500">
                            <Plus className="h-5 w-5" />
                        </Button>
                        <button
                            onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                            className={cn(
                                "flex items-center gap-1 text-xs font-medium px-2 py-1 rounded transition-colors",
                                mode === 'workflow' ? "text-amber-600 bg-amber-50" : "text-blue-600 bg-blue-50"
                            )}
                        >
                            {mode === 'workflow' ? "⚡ Workflow Mode" : "👣 Step Mode"}
                        </button>
                    </div>
                    <Button variant="ghost" size="icon" className="h-9 w-9 text-blue-600 hover:bg-blue-50">
                        <Send className="h-5 w-5" />
                    </Button>
                </div>
            </div>
        </div>
    )
}

function InputDemo3() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-gray-100 p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl bg-white rounded-xl shadow-sm p-2">
                <Textarea
                    placeholder="What's next?"
                    className="w-full border-none shadow-none focus-visible:ring-0 resize-none p-3 min-h-[60px] text-gray-700 bg-transparent"
                />
                <div className="flex justify-between items-center px-1 pt-2 border-t border-gray-100 mt-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:bg-gray-100 rounded-lg">
                        <Plus className="h-5 w-5" />
                    </Button>
                    <div className="flex items-center gap-3">
                        <div className="flex bg-gray-100 p-0.5 rounded-lg">
                            <button
                                onClick={() => setMode('workflow')}
                                className={cn("px-3 py-1 text-xs font-medium rounded-md transition-all", mode === 'workflow' ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700")}
                            >
                                Think
                            </button>
                            <button
                                onClick={() => setMode('step')}
                                className={cn("px-3 py-1 text-xs font-medium rounded-md transition-all", mode === 'step' ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700")}
                            >
                                Step
                            </button>
                        </div>
                        <Button size="icon" className="h-8 w-8 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                            <ArrowUp className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function InputDemo4() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl bg-white/60 backdrop-blur-xl border border-white/50 shadow-sm rounded-2xl p-1.5 flex gap-2 items-end">
                <Button size="icon" variant="ghost" className="h-10 w-10 shrink-0 rounded-xl text-gray-500 hover:bg-white/50">
                    <Plus className="h-5 w-5" />
                </Button>
                <div className="flex-1 relative">
                    <Textarea
                        placeholder="Message..."
                        className="w-full bg-transparent border-none shadow-none focus-visible:ring-0 resize-none py-2.5 px-0 min-h-[44px] text-gray-800 placeholder:text-gray-500/70"
                    />
                    <div className="flex gap-2 pb-2">
                        <button
                            onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                            className="bg-white/50 hover:bg-white/80 border border-white/60 px-2 py-0.5 rounded-md text-[10px] font-semibold text-gray-600 transition-colors uppercase tracking-wide cursor-pointer"
                        >
                            {mode === 'workflow' ? '✨ Workflow' : '🔨 Step-by-Step'}
                        </button>
                    </div>
                </div>
                <Button size="icon" className="h-10 w-10 shrink-0 rounded-xl bg-gray-900/90 text-white hover:bg-gray-900 shadow-lg">
                    <ArrowUp className="h-5 w-5" />
                </Button>
            </div>
        </div>
    )
}

function InputDemo5() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-white p-10 rounded-2xl flex justify-center border border-gray-100">
            <div className="w-full max-w-2xl bg-gray-50 rounded-[20px] p-2 flex flex-col gap-2 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100 transition-all">
                <div className="flex items-start gap-2 px-2">
                    <button
                        onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                        className="mt-2 shrink-0 flex items-center gap-1 bg-white border border-gray-200 shadow-sm px-2 py-1 rounded-full text-xs font-semibold text-gray-700 hover:border-gray-300 transition-colors"
                    >
                        {mode === 'workflow' ? <Sparkles className="h-3 w-3 text-purple-500" /> : <Layers className="h-3 w-3 text-blue-500" />}
                        {mode === 'workflow' ? 'Think' : 'Step'}
                    </button>
                    <Textarea
                        placeholder="Type your instruction..."
                        className="w-full bg-transparent border-none shadow-none focus-visible:ring-0 resize-none py-2 min-h-[44px] text-gray-800"
                    />
                </div>
                <div className="flex justify-between items-center px-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:bg-gray-200/50 rounded-full">
                        <Plus className="h-5 w-5" />
                    </Button>
                    <Button size="sm" className="bg-black text-white rounded-full hover:bg-gray-800 h-8 px-4 text-xs font-medium">
                        Send <ArrowRight className="ml-1 h-3 w-3" />
                    </Button>
                </div>
            </div>
        </div>
    )
}

function InputDemo6() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-[#f2f4f6] p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl bg-[#e3e6ea] p-1.5 rounded-[28px] flex items-end gap-1.5">
                <Button size="icon" className="h-10 w-10 rounded-full bg-white text-gray-600 shadow-sm hover:scale-105 transition-transform shrink-0">
                    <Plus className="h-5 w-5" />
                </Button>
                <div className="flex-1 bg-white rounded-[24px] px-4 py-1.5 shadow-sm flex flex-col min-h-[48px]">
                    <Textarea
                        placeholder="Message..."
                        className="w-full bg-transparent border-none shadow-none focus-visible:ring-0 resize-none p-0 min-h-[24px] text-gray-800 leading-6 py-1"
                    />
                    <div className="flex justify-end pb-1">
                        <button
                            onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                            className="text-[10px] uppercase font-bold tracking-wider text-gray-400 hover:text-blue-600 transition-colors"
                        >
                            {mode === 'workflow' ? '● Workflow Mode' : '○ Step Mode'}
                        </button>
                    </div>
                </div>
                <Button size="icon" className="h-11 w-11 rounded-[20px] bg-blue-600 text-white shadow-md hover:bg-blue-700 shrink-0">
                    <ArrowUp className="h-6 w-6" />
                </Button>
            </div>
        </div>
    )
}

function InputDemo7() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-white p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl space-y-2">
                <div className="flex items-center gap-4 text-sm font-medium text-gray-500 mb-2 pl-1">
                    <button onClick={() => setMode('workflow')} className={cn("hover:text-black transition-colors pb-1 border-b-2", mode === 'workflow' ? "text-black border-black" : "border-transparent")}>Workflow</button>
                    <button onClick={() => setMode('step')} className={cn("hover:text-black transition-colors pb-1 border-b-2", mode === 'step' ? "text-black border-black" : "border-transparent")}>Step-by-Step</button>
                </div>
                <div className="relative">
                    <Textarea
                        placeholder="Enter your command..."
                        className="w-full border-b border-gray-200 focus:border-black rounded-none border-t-0 border-l-0 border-r-0 px-0 py-2 resize-none shadow-none focus-visible:ring-0 min-h-[50px] text-xl font-light"
                    />
                    <div className="absolute right-0 bottom-3 flex gap-2">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-black">
                            <Plus className="h-5 w-5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-black">
                            <ArrowRight className="h-5 w-5" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}

function InputDemo8() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-slate-50 p-10 rounded-2xl flex justify-center">
            <div className="w-full max-w-2xl bg-white border border-slate-200 rounded-lg flex flex-col shadow-sm">
                <div className="flex items-center justify-between bg-slate-50 border-b border-slate-100 px-3 py-1.5 rounded-t-lg">
                    <div className="flex items-center gap-1 bg-white border border-slate-200 rounded px-1 p-0.5">
                        <button onClick={() => setMode('workflow')} className={cn("px-2 py-0.5 text-[10px] font-medium rounded transition-colors", mode === 'workflow' ? "bg-slate-800 text-white" : "text-slate-500 hover:bg-slate-100")}>WORKFLOW</button>
                        <button onClick={() => setMode('step')} className={cn("px-2 py-0.5 text-[10px] font-medium rounded transition-colors", mode === 'step' ? "bg-slate-800 text-white" : "text-slate-500 hover:bg-slate-100")}>STEP</button>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">AI-AGENT-OS v2.0</span>
                </div>
                <Textarea
                    placeholder="Input..."
                    className="w-full border-none shadow-none focus-visible:ring-0 resize-none p-3 min-h-[60px] text-slate-700 bg-transparent font-sans"
                />
                <div className="flex justify-between p-2 pt-0">
                    <Button variant="outline" size="sm" className="h-7 w-7 p-0 border-slate-200 text-slate-500 hover:bg-slate-50">
                        <Plus className="h-4 w-4" />
                    </Button>
                    <Button size="sm" className="h-7 bg-slate-900 text-white hover:bg-slate-800 text-xs px-3">
                        SUBMIT
                    </Button>
                </div>
            </div>
        </div>
    )
}

function InputDemo9() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    return (
        <div className="bg-white p-10 rounded-2xl flex justify-center border border-dashed border-gray-200">
            <div className="w-full max-w-2xl relative pl-12">
                <Button size="icon" className="absolute left-0 top-1 h-9 w-9 rounded-full bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-100 shadow-sm">
                    <Plus className="h-5 w-5" />
                </Button>

                <Textarea
                    placeholder="Start typing..."
                    className="w-full border-none shadow-none focus-visible:ring-0 resize-none py-2 px-0 min-h-[48px] text-lg text-gray-800 placeholder:text-gray-300 bg-transparent"
                />

                <div className="flex items-center justify-between border-t border-gray-100 pt-2 mt-1">
                    <button
                        onClick={() => setMode(mode === 'workflow' ? 'step' : 'workflow')}
                        className="text-xs font-medium text-gray-400 hover:text-gray-900 transition-colors flex items-center gap-1.5"
                    >
                        <span className={cn("w-2 h-2 rounded-full", mode === 'workflow' ? "bg-green-500" : "bg-orange-500")}></span>
                        {mode === 'workflow' ? 'Automatic Workflow' : 'Manual Steps'}
                    </button>
                    <Button variant="ghost" size="sm" className="text-blue-600 hover:bg-blue-50 font-semibold pr-2">
                        Send <ArrowRight className="ml-1 h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    )
}

function InputDemo10() {
    const [mode, setMode] = useState<'workflow' | 'step'>('workflow')
    const [focused, setFocused] = useState(false)

    return (
        <div className="bg-gray-50 p-10 rounded-2xl flex justify-center">
            <div className={cn(
                "w-full max-w-xl transition-all duration-300 ease-out flex flex-col justify-end bg-white shadow-xl rounded-[32px] overflow-hidden border border-gray-100",
                focused ? "min-h-[140px]" : "min-h-[60px]"
            )}>
                <div className="flex items-center px-2 pt-2">
                    <Button variant="ghost" size="icon" className="h-10 w-10 text-gray-400 hover:bg-gray-100 rounded-full shrink-0">
                        <Plus className="h-6 w-6" />
                    </Button>
                    <Textarea
                        placeholder="What's on your mind?"
                        className="border-none shadow-none focus-visible:ring-0 resize-none py-3 px-3 min-h-[44px] text-gray-800 bg-transparent"
                        onFocus={() => setFocused(true)}
                        onBlur={() => setFocused(false)}
                    />
                    {!focused && (
                        <Button size="icon" className="h-10 w-10 rounded-full bg-black text-white shrink-0 mr-1">
                            <ArrowUp className="h-5 w-5" />
                        </Button>
                    )}
                </div>

                {focused && (
                    <div className="flex justify-between items-center px-4 pb-3 pt-2 bg-gray-50/50 animate-in slide-in-from-bottom-2 fade-in">
                        <div className="flex bg-gray-200/50 p-1 rounded-full">
                            <button
                                onClick={() => setMode('workflow')}
                                className={cn("px-3 py-1.5 rounded-full text-xs font-semibold transition-all", mode === 'workflow' ? "bg-white shadow text-black" : "text-gray-500 hover:text-gray-700")}
                            >
                                Workflow
                            </button>
                            <button
                                onClick={() => setMode('step')}
                                className={cn("px-3 py-1.5 rounded-full text-xs font-semibold transition-all", mode === 'step' ? "bg-white shadow text-black" : "text-gray-500 hover:text-gray-700")}
                            >
                                Step
                            </button>
                        </div>
                        <Button size="icon" className="h-9 w-9 rounded-full bg-black text-white shadow-lg hover:scale-105 transition-transform">
                            <ArrowUp className="h-5 w-5" />
                        </Button>
                    </div>
                )}
            </div>
        </div>
    )
}
