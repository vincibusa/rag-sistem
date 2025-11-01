'use client'

import { useState, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Upload, FileText, X, CheckCircle2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface UploadedFile {
	id: string
	file: File
	status: 'uploading' | 'success' | 'error'
	progress: number
	error?: string
}

const ACCEPTED_FILE_TYPES = {
	'application/pdf': ['.pdf'],
	'application/msword': ['.doc'],
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
	'application/vnd.ms-excel': ['.xls'],
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
	'text/plain': ['.txt'],
}

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB

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
		default:
			return 'Unknown'
	}
}

export default function UploadPage() {
	const [files, setFiles] = useState<UploadedFile[]>([])
	const [isDragging, setIsDragging] = useState(false)

	const validateFile = useCallback((file: File): string | null => {
		if (!Object.keys(ACCEPTED_FILE_TYPES).includes(file.type) && 
				!file.name.match(/\.(pdf|doc|docx|xls|xlsx|txt)$/i)) {
			return 'Formato file non supportato. Supportati: PDF, DOC, DOCX, XLS, XLSX, TXT'
		}
		if (file.size > MAX_FILE_SIZE) {
			return `File troppo grande. Dimensione massima: ${MAX_FILE_SIZE / 1024 / 1024}MB`
		}
		return null
	}, [])

	const handleFiles = useCallback((fileList: FileList | null) => {
		if (!fileList) return

		const newFiles: UploadedFile[] = Array.from(fileList)
			.filter((file) => {
				const error = validateFile(file)
				if (error) {
					// TODO: Mostrare toast di errore
					console.error(error)
					return false
				}
				return true
			})
			.map((file) => ({
				id: `${Date.now()}-${Math.random()}`,
				file,
				status: 'uploading' as const,
				progress: 0,
			}))

		setFiles((prev) => [...prev, ...newFiles])

		// Simula upload progress
		newFiles.forEach((uploadedFile) => {
			const simulateUpload = () => {
				setFiles((prev) =>
					prev.map((f) => {
						if (f.id === uploadedFile.id) {
							if (f.progress >= 100) {
								return { ...f, status: 'success' as const, progress: 100 }
							}
							return { ...f, progress: f.progress + 10 }
						}
						return f
					})
				)

				const currentFile = newFiles.find((f) => f.id === uploadedFile.id)
				if (currentFile && currentFile.progress < 100) {
					setTimeout(simulateUpload, 200)
				}
			}
			simulateUpload()
		})

		// TODO: Implementare upload reale
		// for (const uploadedFile of newFiles) {
		//   await uploadFile(uploadedFile.file)
		// }
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
		},
		[handleFiles]
	)

	const removeFile = useCallback((id: string) => {
		setFiles((prev) => prev.filter((f) => f.id !== id))
	}, [])

	const completedCount = files.filter((f) => f.status === 'success').length
	const errorCount = files.filter((f) => f.status === 'error').length
	const uploadingCount = files.filter((f) => f.status === 'uploading').length

	return (
		<div className="space-y-4 md:space-y-6">
			<div>
				<h2 className="text-2xl md:text-3xl font-bold tracking-tight">Upload Documenti</h2>
				<p className="text-sm md:text-base text-muted-foreground mt-1">
					Carica documenti in formato PDF, DOC, DOCX, XLS, XLSX, TXT
				</p>
			</div>

			<Card>
				<CardHeader>
					<CardTitle>Carica Documenti</CardTitle>
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
							'border-2 border-dashed rounded-lg p-6 md:p-12 text-center transition-colors',
							isDragging
								? 'border-primary bg-primary/5'
								: 'border-muted-foreground/25 hover:border-primary/50'
						)}
					>
						<Upload className="h-8 w-8 md:h-12 md:w-12 mx-auto mb-4 text-muted-foreground" />
						<p className="text-sm md:text-base font-medium mb-2">
							Trascina i file qui o
						</p>
						<Button
							onClick={() => document.getElementById('file-input')?.click()}
							variant="outline"
							size="sm"
							className="mb-2"
						>
							Sfoglia
						</Button>
						<p className="text-xs md:text-sm text-muted-foreground">
							Massimo {MAX_FILE_SIZE / 1024 / 1024}MB per file
						</p>
						<input
							id="file-input"
							type="file"
							multiple
							accept=".pdf,.doc,.docx,.xls,.xlsx,.txt"
							onChange={handleFileInput}
							className="hidden"
						/>
					</div>
				</CardContent>
			</Card>

			{(files.length > 0 || completedCount > 0) && (
				<Card>
					<CardHeader>
						<CardTitle>File Caricati</CardTitle>
						<CardDescription>
							{completedCount} completati, {uploadingCount} in corso, {errorCount} errori
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-3">
						{files.map((file) => (
							<div
								key={file.id}
								className="flex flex-col gap-2 p-3 border rounded-lg bg-card"
							>
								<div className="flex items-start gap-3">
									<FileText className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
									<div className="flex-1 min-w-0">
										<p className="text-sm font-medium truncate">{file.file.name}</p>
										<div className="flex items-center gap-2 mt-1">
											<span className="text-xs text-muted-foreground">
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
												className="h-8 w-8"
											>
												<X className="h-4 w-4" />
											</Button>
										)}
									</div>
								</div>

								{file.status === 'uploading' && (
									<div className="space-y-1">
										<Progress value={file.progress} className="h-2" />
										<p className="text-xs text-muted-foreground text-right">
											{file.progress}%
										</p>
									</div>
								)}

								{file.status === 'error' && file.error && (
									<Alert variant="destructive" className="py-2">
										<AlertDescription className="text-xs">
											{file.error}
										</AlertDescription>
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
