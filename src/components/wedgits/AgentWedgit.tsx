import React from 'react'

type Props = {
  id: string
  label: string
  onDrop?: (type: string, id: string) => void
	state?: { replicated?: boolean; locked?: boolean; alert?: boolean, safeguard?: {decision?: string, entry?: string, reason?: string} }
}

export default function AgentWedgit({id, label, onDrop, state}: Props){
  const handleDragStart = (e: React.DragEvent) => {
	e.dataTransfer.setData('text/plain', JSON.stringify({type: 'agent', id}))
  }

  const handleDragOver = (e: React.DragEvent) => {
	e.preventDefault()
  }

  const handleDrop = (e: React.DragEvent) => {
	e.preventDefault()
	const raw = e.dataTransfer.getData('text/plain')
	try {
	  const payload = JSON.parse(raw)
	  if (onDrop) onDrop(payload.type, id)
	} catch (err) {
	  // ignore
	}
  }

  const classes = ['agent-wedgit']
  if(state?.replicated) classes.push('replicated')
  if(state?.locked) classes.push('locked')
  if(state?.alert) classes.push('alert')

  const [hover, setHover] = React.useState(false)

  return (
	<div className={classes.join(' ')} draggable onDragStart={handleDragStart} onDragOver={handleDragOver} onDrop={handleDrop} style={{position:'relative', padding:8}} onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)}>
	  <div className="wedgit-label">{label}</div>
	  {state?.replicated && <div style={{position:'absolute', top:4, right:4, background:'#0a0', color:'#fff', padding:'2px 6px', borderRadius:4, fontSize:11}}>Replicated</div>}
	  {state?.locked && <div style={{position:'absolute', bottom:4, right:4, background:'#06f', color:'#fff', padding:'2px 6px', borderRadius:4, fontSize:11}}>Shield</div>}
	  {state?.alert && <div style={{position:'absolute', bottom:4, left:4, background:'#f33', color:'#fff', padding:'2px 6px', borderRadius:4, fontSize:11}}>Alert</div>}
		{hover && state?.safeguard && (
		<div className="agent-tooltip">
		  <div>Last SafeGuard decision: <strong>{state.safeguard.decision || 'N/A'}</strong></div>
		  <div className="muted">DataVault Entry: {state.safeguard.entry || 'unknown'}</div>
		  <div className="muted">Reason: {state.safeguard.reason || '—'}</div>
		</div>
	  )}
	</div>
  )
}
