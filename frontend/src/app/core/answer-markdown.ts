import { Component, computed, input } from '@angular/core';

type Inline = { text:string; emphasis:'bold'|'italic'|null };
type Block = { kind:'paragraph'|'list'; lines:Inline[][] };

/** A deliberately small Markdown subset rendered through Angular text bindings, never HTML. */
@Component({standalone:true,selector:'cs-answer-markdown',template:`
  <div class="answer-markdown">@for(block of blocks();track $index){
    @if(block.kind==='list'){
      <ul>@for(line of block.lines;track $index){<li>@for(part of line;track $index){
        @if(part.emphasis==='bold'){<strong>{{part.text}}</strong>}
        @else if(part.emphasis==='italic'){<em>{{part.text}}</em>}
        @else { {{part.text}} }
      }</li>}</ul>
    }@else{
      @for(line of block.lines;track $index){<p>@for(part of line;track $index){
        @if(part.emphasis==='bold'){<strong>{{part.text}}</strong>}
        @else if(part.emphasis==='italic'){<em>{{part.text}}</em>}
        @else { {{part.text}} }
      }</p>}
    }
  }</div>
`})
export class AnswerMarkdown {
  readonly text=input.required<string>();
  readonly blocks=computed(()=>{
    const blocks:Block[]=[];
    for(const paragraph of this.text().trim().split(/\n\s*\n/)){
      if(!paragraph.trim())continue;
      const lines=paragraph.trim().split('\n');
      const list=lines.every(line=>/^\s*[-*] /.test(line));
      blocks.push({kind:list?'list':'paragraph',lines:lines.map(line=>this.inline(list?line.replace(/^\s*[-*] /,''):line))});
    }
    return blocks;
  });

  private inline(line:string):Inline[]{
    const parts:Inline[]=[];
    const markers=/\*\*([^*\n]+)\*\*|\*([^*\n]+)\*/g;
    let start=0;
    for(const match of line.matchAll(markers)){
      const index=match.index??0;
      if(index>start)parts.push({text:line.slice(start,index),emphasis:null});
      parts.push({text:match[1]??match[2]??'',emphasis:match[1]?'bold':'italic'});
      start=index+match[0].length;
    }
    if(start<line.length)parts.push({text:line.slice(start),emphasis:null});
    return parts;
  }
}
