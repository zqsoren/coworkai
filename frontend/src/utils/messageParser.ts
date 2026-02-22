/**
 * 消息解析工具
 * 用于解析不同 persona 模式下的 Agent 输出
 */

export interface ParsedMessage {
    answer: string       // 回答部分
    reasoning?: string   // 思考部分（仅 efficient 模式）
    mode: 'normal' | 'efficient' | 'concise'
}

/**
 * 解析消息内容
 * @param content - 原始消息内容
 * @param personaMode - Agent 的人设模式
 * @returns 解析后的消息对象
 */
export function parseMessage(content: string, personaMode: string = 'normal'): ParsedMessage {
    if (personaMode === 'efficient') {
        // 尝试解析【回答】和【思考】标签
        const answerMatch = content.match(/【回答】\s*([\s\S]*?)(?=【思考】|$)/);
        const reasoningMatch = content.match(/【思考】\s*([\s\S]*)/);

        if (answerMatch) {
            return {
                answer: answerMatch[1].trim(),
                reasoning: reasoningMatch ? reasoningMatch[1].trim() : undefined,
                mode: 'efficient'
            };
        }

        // 如果没有匹配到格式，回退到全文显示
        return {
            answer: content,
            mode: 'efficient'
        };
    }

    // 普通和精简模式：直接返回原文
    return {
        answer: content,
        mode: personaMode as any
    };
}
