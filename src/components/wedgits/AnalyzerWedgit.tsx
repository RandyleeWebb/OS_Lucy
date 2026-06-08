import React from 'react'
// file loaded for next edits

type Props = {
  onBindAgent?: (agentId: string) => void
}

export default function AnalyzerWedgit({onBindAgent}: Props){
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault() }
  const handleDrop = (e: React.DragEvent) => {
	e.preventDefault()
	const raw = e.dataTransfer.getData('text/plain')
	try{
	  const payload = JSON.parse(raw)
	  if(payload.type === 'agent' && onBindAgent) onBindAgent(payload.id)
	}catch(err){}
  }

  return (
	  <div className="analyzer-wedgit" onDragOver={handleDragOver} onDrop={handleDrop} style={{padding:12, border:'2px solid #444', minWidth:140}}>
	  <div className="analyzer-label">Analyzer</div>
	</div>
  )
}
