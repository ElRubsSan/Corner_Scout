/** Reviewed, locally hosted image allowlist. Never infer an image from a name or URL. */
import { clubNames, playerNames } from './visual-entities.generated';
import { playerPhotoSources } from './player-photo-sources.generated';
import { manualPhotoSources } from './manual-photo-sources.generated';
import { userTakerPhotos } from './user-taker-photos.generated';

const playerPhotos:Record<number,{name:string;file:string}> = {
  ...Object.fromEntries(playerPhotoSources.map(photo=>[photo.id,{name:photo.name,file:`/media/players/${photo.id}.webp`}])),
  ...Object.fromEntries(manualPhotoSources.map(photo=>[photo.id,{name:photo.name,file:`/media/players/${photo.id}.webp`}])),
  ...Object.fromEntries(Object.entries(userTakerPhotos).map(([id,name])=>[Number(id),{name,file:`/media/players/${id}.webp`}])),
  6396:{name:'Beñat Etxebarria Urkiaga',file:'/media/players/6396.webp'},
  26848:{name:'Roberto Trashorras Gayoso',file:'/media/players/26848.webp'}
};

export function playerImage(name:string,id:number|null):string|null {
  if(id===null)return null;
  if(playerNames[id]!==name)return null;
  const photo=playerPhotos[id];
  return photo?.name===name?photo.file:null;
}

export function clubImage(name:string,id:number|null|undefined):string|null {
  if(id==null)return null;
  if(clubNames[id]!==name)return null;
  return `/media/clubs/${id}.png`;
}
