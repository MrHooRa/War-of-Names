import { useState } from 'react'

/**
 * JsonEditorToggle — adds Form/JSON mode toggle to admin modals.
 *
 * Props:
 *  - mode: 'form' | 'json'
 *  - onModeChange: (mode) => void
 *  - jsonValue: string
 *  - onJsonChange: (str) => void
 *  - template: object | array — the example JSON structure
 *  - templateLabel: string — button text like "قالب عنصر"
 *  - bulkTemplate: array — example for bulk import (array of items)
 *  - error: string | null
 */
export default function JsonEditorToggle({ mode, onModeChange, jsonValue, onJsonChange, template, templateLabel, bulkTemplate, error }) {
  return (
    <div className="space-y-3">
      {/* Mode toggle */}
      <div className="flex items-center gap-2">
        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
          <button type="button" onClick={() => onModeChange('form')}
            className={`px-3 py-1 rounded-md text-xs font-bold smooth-transition ${mode === 'form' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500'}`}>
            نموذج
          </button>
          <button type="button" onClick={() => onModeChange('json')}
            className={`px-3 py-1 rounded-md text-xs font-bold smooth-transition ${mode === 'json' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500'}`}>
            JSON
          </button>
        </div>

        {mode === 'json' && (
          <div className="flex gap-1.5 mr-auto">
            {template && (
              <button type="button" onClick={() => onJsonChange(JSON.stringify(template, null, 2))}
                className="text-[10px] font-bold text-brand-teal dark:text-brand-slate bg-brand-teal/10 dark:bg-brand-slate/20 px-2 py-1 rounded-md hover:bg-brand-teal/20 smooth-transition">
                {templateLabel || 'قالب'}
              </button>
            )}
            {bulkTemplate && (
              <button type="button" onClick={() => onJsonChange(JSON.stringify(bulkTemplate, null, 2))}
                className="text-[10px] font-bold text-amber-500 bg-amber-500/10 px-2 py-1 rounded-md hover:bg-amber-500/20 smooth-transition">
                قالب متعدد
              </button>
            )}
          </div>
        )}
      </div>

      {/* JSON Editor */}
      {mode === 'json' && (
        <div className="space-y-2">
          <textarea
            value={jsonValue}
            onChange={e => onJsonChange(e.target.value)}
            dir="ltr"
            className="w-full h-64 bg-gray-950 text-green-400 font-mono text-xs p-4 rounded-xl border border-gray-700 focus:border-brand-teal focus:outline-none resize-y"
            placeholder='{"name": "...", "description": "..."}'
            spellCheck={false}
          />
          {error && <p className="text-brand-danger text-xs font-bold">{error}</p>}
          <p className="text-[10px] text-gray-500">يمكنك لصق JSON من أي مصدر (مثل ChatGPT أو أي LLM). للإنشاء المتعدد، استخدم مصفوفة [...]</p>
        </div>
      )}
    </div>
  )
}

/**
 * parseJsonInput — parses JSON string and returns items array + error.
 * Accepts both single object and array of objects.
 * Returns { items: array | null, error: string | null }
 */
export function parseJsonInput(jsonStr) {
  try {
    const parsed = JSON.parse(jsonStr)
    if (Array.isArray(parsed)) {
      if (parsed.length === 0) return { items: null, error: 'المصفوفة فارغة' }
      return { items: parsed, error: null }
    }
    if (typeof parsed === 'object' && parsed !== null) {
      return { items: [parsed], error: null }
    }
    return { items: null, error: 'يجب أن يكون JSON كائناً أو مصفوفة' }
  } catch (e) {
    return { items: null, error: `خطأ في صيغة JSON: ${e.message}` }
  }
}
