import React, { useState } from 'react';
import { Button } from './ui/button';
import { CheckCircle2, XCircle, AlertCircle, Play, ChevronDown, ChevronRight } from 'lucide-react';

interface WorkflowStep {
    step: number;
    step_name: string;
    executor_agent: string;
    executor_prompt: string;
    reviewer_agent: string | null;
    reviewer_prompt: string | null;
    max_revision_rounds: number;
}

interface Workflow {
    plan_name: string;
    description: string;
    workflow: WorkflowStep[];
}

interface WorkflowViewerProps {
    workflow: Workflow;
    onExecute?: () => void;
    onCancel?: () => void;
    readOnly?: boolean;
}

export const WorkflowViewer: React.FC<WorkflowViewerProps> = ({ workflow, onExecute, onCancel, readOnly: _readOnly }) => {
    const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([1]));

    const toggleStep = (stepNum: number) => {
        const newExpanded = new Set(expandedSteps);
        if (newExpanded.has(stepNum)) {
            newExpanded.delete(stepNum);
        } else {
            newExpanded.add(stepNum);
        }
        setExpandedSteps(newExpanded);
    };

    return (
        <div className="space-y-3 p-2 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-900 rounded-lg">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-blue-600" />
                        执行计划预览
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {workflow.plan_name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                        {workflow.description}
                    </p>
                </div>
                <div className="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 px-3 py-1 rounded-full text-sm border border-blue-200 dark:border-blue-800">
                    {workflow.workflow.length} 个步骤
                </div>
            </div>

            {/* Workflow Steps */}
            <div className="space-y-3">
                {workflow.workflow.map((step) => {
                    const isExpanded = expandedSteps.has(step.step);
                    const hasReviewer = !!step.reviewer_agent;

                    return (
                        <div key={step.step} className="bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                            {/* Step Header */}
                            <div
                                className="p-4 bg-white dark:bg-gray-800 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
                                onClick={() => toggleStep(step.step)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3 flex-1">
                                        <div className="flex items-center gap-2">
                                            {isExpanded ? (
                                                <ChevronDown className="w-4 h-4 text-gray-500" />
                                            ) : (
                                                <ChevronRight className="w-4 h-4 text-gray-500" />
                                            )}
                                            <div className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-semibold">
                                                步骤 {step.step}
                                            </div>
                                        </div>
                                        <span className="font-semibold text-gray-900 dark:text-white">
                                            {step.step_name}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="px-2 py-1 rounded text-xs border border-gray-300 dark:border-gray-600">
                                            {step.executor_agent}
                                        </div>
                                        {hasReviewer && (
                                            <>
                                                <span className="text-gray-400">→</span>
                                                <div className="text-xs bg-yellow-50 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-200 px-2 py-1 rounded border border-yellow-200 dark:border-yellow-800">
                                                    审核: {step.reviewer_agent}
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Step Details (Expandable) */}
                            {isExpanded && (
                                <div className="p-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 space-y-3">
                                    {/* Executor Prompt */}
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <Play className="w-4 h-4 text-blue-600" />
                                            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                                                执行指令
                                            </span>
                                        </div>
                                        <div className="bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                                            <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                                                {step.executor_prompt}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Reviewer Prompt */}
                                    {hasReviewer && (
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <CheckCircle2 className="w-4 h-4 text-yellow-600" />
                                                <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                                                    审核标准
                                                </span>
                                                <div className="text-xs px-2 py-1 rounded border border-gray-300 dark:border-gray-600">
                                                    最多修改 {step.max_revision_rounds} 次
                                                </div>
                                            </div>
                                            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded border border-yellow-200 dark:border-yellow-800">
                                                <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
                                                    {step.reviewer_prompt}
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Placeholder Detection */}
                                    {(step.executor_prompt.includes('{') || (step.reviewer_prompt && step.reviewer_prompt.includes('{'))) && (
                                        <div className="flex items-start gap-2 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                            <span>包含动态变量占位符，执行时自动填充</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
                <Button
                    onClick={onExecute}
                    className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold"
                >
                    <Play className="w-4 h-4 mr-2" />
                    确认执行计划
                </Button>
                <Button
                    onClick={onCancel}
                    variant="outline"
                    className="px-6"
                >
                    <XCircle className="w-4 h-4 mr-2" />
                    取消
                </Button>
            </div>
        </div>
    );
};
