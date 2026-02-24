import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { downloadBlob } from '@/lib/utils'
import * as XLSX from 'xlsx'

interface ExportButtonProps {
  data: Record<string, unknown>[]
  filename?: string
  sheetName?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

export function ExportButton({
  data,
  filename = 'exportacion',
  sheetName = 'Datos',
  variant = 'outline',
  size = 'sm',
}: ExportButtonProps) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    if (!data.length) return
    setExporting(true)

    await new Promise((resolve) => setTimeout(resolve, 100)) // allow render

    try {
      const ws = XLSX.utils.json_to_sheet(data)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, sheetName)
      const buffer = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      downloadBlob(blob, `${filename}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <Button variant={variant} size={size} onClick={handleExport} disabled={exporting || !data.length}>
      {exporting ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Download className="h-4 w-4" />
      )}
      {size !== 'icon' && <span className="ml-2">Excel</span>}
    </Button>
  )
}
