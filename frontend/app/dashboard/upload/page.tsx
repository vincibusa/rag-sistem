'use client'

import { useState, useCallback, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Upload, FileText, X, CheckCircle2, AlertCircle, CloudUpload, FileCheck, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { uploadDocuments, ApiClientError } from '@/lib/api-client'
import type { DocumentSummary } from '@/lib/types'

interface UploadedFile {
	id: string
	file: File
	status: 'uploading' | 'success' | 'error'
	progress: number
	error?: string
	documentId?: string
}

const ACCEPTED_FILE_TYPES = {
	'application/pdf': ['.pdf'],
	'application/msword': ['.doc'],
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
	'application/vnd.ms-excel': ['.xls'],
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
	'text/plain': ['.txt'],
	'application/zip': ['.zip'],
	'application/x-zip-compressed': ['.zip'],
}

const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB

function getFileType(file: File): string {
	const ext = file.name.split('.').pop()?.toLowerCase()
	switch (ext) {
		case 'pdf':
			return 'PDF'
		case 'doc':
		case 'docx':
			return 'Word'
		case 'xls':
		case 'xlsx':
			return 'Excel'
	case 'txt':
		return 'Text'
	case 'zip':
		return 'Archivio'
	default:
		return 'Unknown'
}
}

function getFileIcon(file: File): string {
	const ext = file.name.split('.').pop()?.toLowerCase()
	return ext || 'file'
}

export default function UploadPage() {
	const [files, setFiles] = useState<UploadedFile[]>([])
	const [isDragging, setIsDragging] = useState(false)
	const [isUploading, setIsUploading] = useState(false)
	const fileInputRef = useRef<HTMLInputElement>(null)

	const validateFile = useCallback((file: File): string | null => {
	if (!Object.keys(ACCEPTED_FILE_TYPES).includes(file.type) && 
			!file.name.match(/\.(pdf|doc|docx|xls|xlsx|txt|zip)$/i)) {
		return 'Formato file non supportato. Supportati: PDF, DOC, DOCX, XLS, XLSX, TXT, ZIP'
		}
		if (file.size > MAX_FILE_SIZE) {
			return `File troppo grande. Dimensione massima: ${MAX_FILE_SIZE / 1024 / 1024}MB`
		}
		return null
	}, [])

	const handleFiles = useCallback((fileList: FileList | null) => {
		if (!fileList) return

		const newFiles: UploadedFile[] = []
		const errors: string[] = []

		Array.from(fileList).forEach((file) => {
			const error = validateFile(file)
			if (error) {
				errors.push(`${file.name}: ${error}`)
				return
			}
			newFiles.push({
				id: `${Date.now()}-${Math.random()}`,
				file,
				status: 'uploading' as const,
				progress: 0,
			})
		})

		if (errors.length > 0) {
			toast.error(`${errors.length} file non validi`, {
				description: errors.slice(0, 3).join(', '),
			})
		}

		if (newFiles.length > 0) {
			setFiles((prev) => [...prev, ...newFiles])
			setIsUploading(true)

			// Upload reale con progress tracking
			const uploadPromises = newFiles.map(async (uploadedFile) => {
				try {
					const response = await uploadDocuments(
						[uploadedFile.file],
						(progressEvent) => {
							if (progressEvent.total) {
								const progress = Math.round(
									(progressEvent.loaded * 100) / progressEvent.total
								)
								setFiles((prev) =>
									prev.map((f) =>
										f.id === uploadedFile.id
											? { ...f, progress: Math.min(progress, 99) }
											: f
									)
								)
							}
						}
					)

					if (response.documents && response.documents.length > 0) {
						const document = response.documents[0]
						setFiles((prev) =>
							prev.map((f) =>
								f.id === uploadedFile.id
									? {
											...f,
											status: 'success' as const,
											progress: 100,
											documentId: document.id,
										}
									: f
							)
						)
						toast.success(`${uploadedFile.file.name} caricato con successo`)
					}
				} catch (error) {
					const errorMessage =
						error instanceof ApiClientError
							? error.detail
							: 'Errore durante il caricamento del file'
					setFiles((prev) =>
						prev.map((f) =>
							f.id === uploadedFile.id
								? { ...f, status: 'error' as const, error: errorMessage }
								: f
						)
					)
					toast.error(`Errore caricamento ${uploadedFile.file.name}`, {
						description: errorMessage,
					})
				}
			})

			Promise.all(uploadPromises).finally(() => {
				setIsUploading(false)
			})
		}
	}, [validateFile])

	const handleDrop = useCallback(
		(e: React.DragEvent) => {
			e.preventDefault()
			setIsDragging(false)
			handleFiles(e.dataTransfer.files)
		},
		[handleFiles]
	)

	const handleDragOver = useCallback((e: React.DragEvent) => {
		e.preventDefault()
		setIsDragging(true)
	}, [])

	const handleDragLeave = useCallback((e: React.DragEvent) => {
		e.preventDefault()
		setIsDragging(false)
	}, [])

	const handleFileInput = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			handleFiles(e.target.files)
			if (fileInputRef.current) {
				fileInputRef.current.value = ''
			}
		},
		[handleFiles]
	)

	const removeFile = useCallback((id: string) => {
		setFiles((prev) => {
			const file = prev.find((f) => f.id === id)
			if (file) {
				toast.info('File rimosso')
			}
			return prev.filter((f) => f.id !== id)
		})
	}, [])

	const clearAll = useCallback(() => {
		setFiles([])
		toast.info('Lista file cancellata')
	}, [])

	const completedCount = files.filter((f) => f.status === 'success').length
	const errorCount = files.filter((f) => f.status === 'error').length
	const uploadingCount = files.filter((f) => f.status === 'uploading').length

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-2">
					<Sparkles className="h-6 w-6 text-primary" />
					Upload Documenti
				</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Carica documenti in formato PDF, DOC, DOCX, XLS, XLSX, TXT
				</p>
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<CloudUpload className="h-5 w-5 text-primary" />
						Carica Documenti
					</CardTitle>
					<CardDescription>
						Trascina i file qui o clicca per selezionare
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div
						onDrop={handleDrop}
						onDragOver={handleDragOver}
						onDragLeave={handleDragLeave}
						className={cn(
							'border-2 border-dashed rounded-xl p-6 md:p-12 text-center cursor-pointer',
							isDragging
								? 'border-primary bg-primary/5'
								: 'border-muted-foreground/25'
						)}
						onClick={() => fileInputRef.current?.click()}
						role="button"
						tabIndex={0}
						onKeyDown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								fileInputRef.current?.click()
							}
						}}
						aria-label="Area upload file"
					>
						<div className="flex flex-col items-center gap-4">
							<div className={cn(
								'rounded-full p-4',
								isDragging ? 'bg-primary/20' : 'bg-primary/10'
							)}>
								<Upload className={cn(
									'h-8 w-8 md:h-12 md:w-12 mx-auto',
									isDragging ? 'text-primary' : 'text-muted-foreground'
								)} />
							</div>
							<div>
								<p className="text-sm md:text-base font-medium mb-2">
									Trascina i file qui o <span className="text-primary font-semibold">clicca per selezionare</span>
								</p>
				<p className="text-xs md:text-sm text-muted-foreground">
					Massimo {MAX_FILE_SIZE / 1024 / 1024}MB per file (≈500MB) • Supportati: PDF, DOC, DOCX, XLS, XLSX, TXT, ZIP
								</p>
							</div>
						</div>
						<input
							ref={fileInputRef}
							type="file"
							multiple
			accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.zip"
							onChange={handleFileInput}
							className="hidden"
							aria-label="Seleziona file"
						/>
					</div>
				</CardContent>
			</Card>

			{files.length > 0 && (
				<Card>
					<CardHeader>
						<div className="flex items-center justify-between">
							<div>
								<CardTitle className="flex items-center gap-2">
									<FileCheck className="h-5 w-5 text-primary" />
									File Caricati
								</CardTitle>
								<CardDescription className="mt-1">
									{completedCount} completati
									{uploadingCount > 0 && ` • ${uploadingCount} in corso`}
									{errorCount > 0 && ` • ${errorCount} errori`}
								</CardDescription>
							</div>
							{files.length > 0 && (
								<Button
									variant="ghost"
									size="sm"
									onClick={clearAll}
									className="text-xs"
								>
									Pulisci tutto
								</Button>
							)}
						</div>
					</CardHeader>
					<CardContent className="space-y-3">
						{files.map((file) => (
							<div
								key={file.id}
								className={cn(
									'flex flex-col gap-2 p-4 border rounded-xl bg-card',
									file.status === 'success' && 'border-green-500/20 bg-green-500/5',
									file.status === 'error' && 'border-destructive/20 bg-destructive/5'
								)}
							>
								<div className="flex items-start gap-3">
									<div className={cn(
										'p-2 rounded-lg flex-shrink-0',
										file.status === 'success' ? 'bg-green-500/10' : file.status === 'error' ? 'bg-destructive/10' : 'bg-muted'
									)}>
										<FileText className={cn(
											'h-5 w-5',
											file.status === 'success' ? 'text-green-600' : file.status === 'error' ? 'text-destructive' : 'text-muted-foreground'
										)} />
									</div>
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium truncate">{file.file.name}</p>
										<div className="flex items-center gap-2 mt-1">
											<span className="text-xs text-muted-foreground font-medium px-2 py-0.5 rounded-md bg-muted">
												{getFileType(file.file)}
											</span>
											<span className="text-xs text-muted-foreground">•</span>
											<span className="text-xs text-muted-foreground">
												{(file.file.size / 1024).toFixed(1)} KB
											</span>
										</div>
									</div>
									<div className="flex items-center gap-2 flex-shrink-0">
										{file.status === 'success' && (
											<CheckCircle2 className="h-5 w-5 text-green-600" />
										)}
										{file.status === 'error' && (
											<AlertCircle className="h-5 w-5 text-destructive" />
										)}
										{file.status !== 'uploading' && (
											<Button
												variant="ghost"
												size="icon"
												onClick={() => removeFile(file.id)}
												className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
												aria-label="Rimuovi file"
											>
												<X className="h-4 w-4" />
											</Button>
										)}
									</div>
								</div>

								{file.status === 'uploading' && (
									<div className="space-y-2">
										<Progress value={file.progress} className="h-2" />
										<div className="flex items-center justify-between text-xs text-muted-foreground">
											<span>Caricamento in corso...</span>
											<span className="font-medium">{file.progress}%</span>
										</div>
									</div>
								)}

								{file.status === 'error' && file.error && (
									<Alert variant="destructive">
										<AlertCircle className="h-4 w-4" />
										<AlertDescription className="text-xs">{file.error}</AlertDescription>
									</Alert>
								)}
							</div>
						))}
					</CardContent>
				</Card>
			)}
		</div>
	)
}
