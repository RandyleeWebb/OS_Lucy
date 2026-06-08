import React from 'react'

type Props = {
  onAttach?: (agentId: string) => void
}

export default function SafeGuardInjector({ onAttach }: Props) {
  const handleDragOver = (e: React.DragEvent) => { e.preventDefault() }
  const handleDrop = (e: React.DragEvent) => {
	e.preventDefault()
	const raw = e.dataTransfer.getData('text/plain')
	try{
	  const payload = JSON.parse(raw)
	  if(payload.type === 'agent' && onAttach) onAttach(payload.id)
	}catch(err){}
  }

  return (
	<div className="safeguard-injector" onDragOver={handleDragOver} onDrop={handleDrop} style={{padding:12, border:'2px solid #06f', minWidth:120}}>
	  <div className="injector-label">SafeGuard Injector</div>
	</div>
  )
}
