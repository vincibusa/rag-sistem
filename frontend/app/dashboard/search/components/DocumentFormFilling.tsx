"use client"

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog'
import { 
  Upload, 
  FileText, 
  Download, 
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  Search,
  FileCheck,
  Sparkles,
  Copy
} from 'lucide-react'
import { toast } from 'sonner'
import { 
  uploadFormDocument, 
  extractFormFields, 
  autoFillForm, 
  downloadFilledForm,
  ApiClientError 
} from '@/lib/api-client'
import type { FormField, FormDocumentUploadResponse, FormFieldExtractionResponse, AutoFillResponse } from '@/lib/types'

interface DocumentFormFillingProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
}

export function DocumentFormFilling({ isOpen, onOpenChange }: DocumentFormFillingProps) {
  const [currentStep, setCurrentStep] = useState<'upload' | 'extract' | 'fill' | 'download'>('upload')
  const [isLoading, setIsLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [formDocument, setFormDocument] = useState<FormDocumentUploadResponse | null>(null)
  const [extractedFields, setExtractedFields] = useState<FormField[]>([])
  const [filledFields, setFilledFields] = useState<FormField[]>([])
  const [autoFillResponse, setAutoFillResponse] = useState<AutoFillResponse | null>(null)
  const [agentGuidance, setAgentGuidance] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const resetState = () => {
    setCurrentStep('upload')
    setIsLoading(false)
    setUploadProgress(0)
    setFormDocument(null)
    setExtractedFields([])
    setFilledFields([])
    setAutoFillResponse(null)
    setAgentGuidance('')
  }

  const handleFileUpload = async (file: File) => {
    if (!file) return

    // Validate file type
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!validTypes.includes(file.type)) {
      toast.error('Tipo file non supportato', {
        description: 'Carica solo file PDF o Word (.docx) con form fields.'
      })
      return
    }

    setIsLoading(true)
    setCurrentStep('upload')

    try {
      const response = await uploadFormDocument(file, (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          setUploadProgress(progress)
        }
      })

      setFormDocument(response)
      toast.success('Documento caricato con successo')
      
      // Move to extraction step
      await handleExtractFields(response.form_id)
    } catch (error) {
      const errorMessage = error instanceof ApiClientError 
        ? error.detail 
        : 'Errore durante il caricamento del documento'
      toast.error('Errore caricamento', { description: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  const handleExtractFields = async (formId: string) => {
    setIsLoading(true)
    setCurrentStep('extract')

    try {
      const response: FormFieldExtractionResponse = await extractFormFields(formId)
      setExtractedFields(response.fields)
      
      if (response.total_fields === 0) {
        toast.warning('Nessun campo trovato', {
          description: 'Il documento potrebbe non contenere form fields riconoscibili.'
        })
      } else {
        toast.success('Campi estratti', {
          description: `Trovati ${response.total_fields} campi da compilare.`
        })
      }

      setCurrentStep('fill')
    } catch (error) {
      const errorMessage = error instanceof ApiClientError 
        ? error.detail 
        : 'Errore durante l\'estrazione dei campi'
      toast.error('Errore estrazione', { description: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  const handleAutoFill = async () => {
    if (!formDocument) return

    setIsLoading(true)

    try {
      const trimmedGuidance = agentGuidance.trim()
      const baseInstruction = 'Compila automaticamente tutti i campi del form.'
      const combinedContext = trimmedGuidance ? `${baseInstruction} ${trimmedGuidance}` : baseInstruction

      const response = await autoFillForm({
        form_id: formDocument.form_id,
        field_names: extractedFields.map(field => field.name),
        search_context: combinedContext,
        agent_guidance: trimmedGuidance || undefined
      })

      setAutoFillResponse(response)
      setFilledFields(response.filled_fields)
      
      toast.success('Auto-compilazione completata', {
        description: `Compilati ${response.total_filled} campi con confidenza media ${(response.average_confidence * 100).toFixed(1)}%`
      })

      setCurrentStep('download')
    } catch (error) {
      const errorMessage = error instanceof ApiClientError 
        ? error.detail 
        : 'Errore durante l\'auto-compilazione'
      toast.error('Errore auto-compilazione', { description: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!formDocument) return

    setIsLoading(true)

    try {
      const blob = await downloadFilledForm(formDocument.form_id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `filled_${formDocument.filename}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success('Documento scaricato', {
        description: 'Il documento compilato è stato scaricato con successo.'
      })

      // Reset and close
      resetState()
      onOpenChange(false)
    } catch (error) {
      const errorMessage = error instanceof ApiClientError 
        ? error.detail 
        : 'Errore durante il download'
      toast.error('Errore download', { description: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopyFilledText = async () => {
    if (!autoFillResponse?.filled_document_text) return
    try {
      await navigator.clipboard.writeText(autoFillResponse.filled_document_text)
      toast.success('Testo compilato copiato negli appunti')
    } catch (error) {
      toast.error('Impossibile copiare il testo', {
        description: error instanceof Error ? error.message : 'Errore sconosciuto'
      })
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800 border-green-200'
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    return 'bg-red-100 text-red-800 border-red-200'
  }

  const getFieldTypeIcon = (fieldType: string) => {
    switch (fieldType.toLowerCase()) {
      case 'text':
      case 'string':
        return '📝'
      case 'date':
        return '📅'
      case 'number':
        return '🔢'
      case 'email':
        return '📧'
      case 'checkbox':
        return '☑️'
      case 'radio':
        return '🔘'
      default:
        return '📄'
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Compilazione Automatica Documenti
          </DialogTitle>
          <DialogDescription>
            Carica un documento con form fields e usa il sistema RAG per compilarlo automaticamente.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto flex flex-col">
          {/* Progress Steps */}
          <div className="flex items-center justify-between text-sm flex-shrink-0 mb-6">
            {['upload', 'extract', 'fill', 'download'].map((step, index) => (
              <div key={step} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                    currentStep === step
                      ? 'bg-primary text-primary-foreground border-primary'
                      : index < ['upload', 'extract', 'fill', 'download'].indexOf(currentStep)
                      ? 'bg-green-100 text-green-600 border-green-300'
                      : 'bg-muted text-muted-foreground border-border'
                  }`}
                >
                  {index < ['upload', 'extract', 'fill', 'download'].indexOf(currentStep) ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    index + 1
                  )}
                </div>
                <span className="ml-2 hidden sm:inline">
                  {step === 'upload' && 'Carica'}
                  {step === 'extract' && 'Estrai'}
                  {step === 'fill' && 'Compila'}
                  {step === 'download' && 'Scarica'}
                </span>
                {index < 3 && (
                  <div
                    className={`w-8 h-0.5 mx-2 ${
                      index < ['upload', 'extract', 'fill', 'download'].indexOf(currentStep)
                        ? 'bg-green-300'
                        : 'bg-border'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Content Area */}
          <ScrollArea className="flex-1 pr-4">
            <div className="space-y-6">
              {/* Upload Step */}
              {currentStep === 'upload' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Upload className="h-5 w-5" />
                      Carica Documento Form
                    </CardTitle>
                    <CardDescription>
                      Carica un documento PDF o Word che contiene form fields da compilare.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center">
                      <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground mb-4">
                        Trascina qui il tuo file o clicca per selezionare
                      </p>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <Button 
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Upload className="h-4 w-4 mr-2" />
                        )}
                        Seleziona File
                      </Button>
                    </div>
                    
                    {isLoading && uploadProgress > 0 && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Caricamento in corso...</span>
                          <span>{uploadProgress}%</span>
                        </div>
                        <Progress value={uploadProgress} className="h-2" />
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Extract Step */}
              {currentStep === 'extract' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Search className="h-5 w-5" />
                      Estrazione Campi in Corso
                    </CardTitle>
                    <CardDescription>
                      Analisi del documento per identificare i campi da compilare...
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="text-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                    <p className="text-sm text-muted-foreground">
                      Sto analizzando il documento per trovare i form fields...
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Fill Step */}
              {currentStep === 'fill' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileCheck className="h-5 w-5" />
                      Campi Identificati
                    </CardTitle>
                    <CardDescription>
                      {extractedFields.length} campi trovati nel documento. Clicca per compilare automaticamente.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 mb-6">
                      <label className="text-sm font-medium">
                        Istruzioni per l&apos;agente
                      </label>
                      <Textarea
                        value={agentGuidance}
                        onChange={(event) => setAgentGuidance(event.target.value)}
                        placeholder="Esempio: usa il contratto di rete firmato nel 2023 e privilegia i dati della società capogruppo."
                        className="min-h-[120px]"
                      />
                      <p className="text-xs text-muted-foreground">
                        Aggiungi indicazioni opzionali per guidare la ricerca (documenti da privilegiare, periodo di riferimento, campi prioritari, ecc.).
                      </p>
                    </div>
                    <div className="space-y-4">
                      {extractedFields.map((field, index) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex items-center gap-3">
                            <span className="text-lg">{getFieldTypeIcon(field.field_type)}</span>
                            <div>
                              <p className="font-medium text-sm">{field.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {field.field_type} • {field.required ? 'Obbligatorio' : 'Opzionale'}
                              </p>
                            </div>
                          </div>
                          <Badge variant="outline" className="capitalize">
                            {field.field_type}
                          </Badge>
                        </div>
                      ))}
                    </div>
                    
                    <div className="mt-6 flex justify-end">
                      <Button 
                        onClick={handleAutoFill}
                        disabled={isLoading || extractedFields.length === 0}
                        className="gap-2"
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Sparkles className="h-4 w-4" />
                        )}
                        Compila Automaticamente
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Download Step */}
              {currentStep === 'download' && autoFillResponse && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      Compilazione Completata
                    </CardTitle>
                    <CardDescription>
                      {autoFillResponse.total_filled} campi compilati con confidenza media del {(autoFillResponse.average_confidence * 100).toFixed(1)}%
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid gap-3">
                        {filledFields.map((field, index) => (
                          <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-lg">{getFieldTypeIcon(field.field_type)}</span>
                                <p className="font-medium text-sm">{field.name}</p>
                              </div>
                              <p className="text-sm text-muted-foreground">{field.value}</p>
                            </div>
                            {field.confidence_score !== null && field.confidence_score !== undefined && (
                              <Badge 
                                variant="outline" 
                                className={getConfidenceColor(field.confidence_score)}
                              >
                                {(field.confidence_score * 100).toFixed(0)}%
                              </Badge>
                            )}
                          </div>
                        ))}
                      </div>

                      {autoFillResponse.search_queries && autoFillResponse.search_queries.length > 0 && (
                        <div className="mt-4 p-3 bg-muted rounded-lg">
                          <p className="text-sm font-medium mb-2">Query di ricerca utilizzate:</p>
                          <ul className="text-sm text-muted-foreground space-y-1">
                            {autoFillResponse.search_queries.map((query, index) => (
                              <li key={index}>• {query}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {autoFillResponse.filled_document_text && (
                        <div className="space-y-2 p-3 border rounded-lg bg-muted/60">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">Documento compilato (testo)</p>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="gap-2"
                              onClick={handleCopyFilledText}
                            >
                              <Copy className="h-4 w-4" />
                              Copia
                            </Button>
                          </div>
                          <ScrollArea className="h-64 border rounded-md bg-background p-3">
                            <pre className="text-sm whitespace-pre-wrap">
                              {autoFillResponse.filled_document_text}
                            </pre>
                          </ScrollArea>
                        </div>
                      )}

                      <div className="flex justify-end gap-3 mt-6">
                        <Button 
                          variant="outline" 
                          onClick={() => setCurrentStep('fill')}
                        >
                          Ricompila
                        </Button>
                        <Button 
                          onClick={handleDownload}
                          disabled={isLoading}
                          className="gap-2"
                        >
                          {isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                          Scarica Documento
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}
