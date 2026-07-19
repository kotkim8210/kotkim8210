/** Hand-authored 16×16 pixel-art portraits for the Cosmic Friends puzzles.
 *  All original artwork (palette-indexed strings, '.' = transparent) —
 *  zero asset files, zero external requests, renders on <canvas>. */

export interface PetArt {
  palette: Record<string, string>;
  rows: string[]; // 16 rows × 16 chars
}

const o = '#241d3d'; // shared cosmic outline
const w = '#ffffff'; // eye glint
const c = '#f7a8b8'; // blush

export const PET_ART: PetArt[] = [
  // 0 — Nova Pup (cream, floppy brown ears, tongue)
  {
    palette: { o, w, c, b: '#a5692f', f: '#f6d9a8', n: '#5a3b28', t: '#f4739c' },
    rows: [
      '................',
      '..ooo......ooo..',
      '.obbbo....obbbo.',
      '.obbbboooobbbbo.',
      '.obbffffffffbbo.',
      'obffffffffffffbo',
      'offfwoffffwofffo',
      'offfooffffoofffo',
      'offffffnnffffffo',
      'ofccfffnnfffccfo',
      'offfffttttfffffo',
      'obffffffffffffbo',
      '.obbffffffffbbo.',
      '..obbbbbbbbbbo..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 1 — Comet Cat (gray, pointy ears, whisker dots)
  {
    palette: { o, w, c, g: '#9aa0b8', f: '#dcdfee', n: '#f4739c' },
    rows: [
      '................',
      '.ogo........ogo.',
      '.oggo......oggo.',
      '.ogggoooooogggo.',
      '.oggggggggggggo.',
      'oggffffffffffggo',
      'ogffwoffffwoffgo',
      'ogffooffffooffgo',
      'ogfffffnnfffffgo',
      'ogcwfffnnfffwcgo',
      'ogffffoffoffffgo',
      'ogffffffffffffgo',
      '.oggffffffffggo.',
      '..oggggggggggo..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 2 — Moon Bunny (white, tall ears with pink lining)
  {
    palette: { o, w, c, u: '#f2f2fb', i: '#f7b8cc', n: '#f4739c' },
    rows: [
      '...oo......oo...',
      '..ouio....ouio..',
      '..ouio....ouio..',
      '..ouuo....ouuo..',
      '.oouuoooooouuoo.',
      '.ouuuuuuuuuuuuo.',
      'ouuuwouuuuwouuuo',
      'ouuuoouuuuoouuuo',
      'ouuuuuunnuuuuuuo',
      'oucuuuunnuuuucuo',
      'ouuuuuuoouuuuuuo',
      '.ouuuuuuuuuuuuo.',
      '.ouuuuuuuuuuuuo.',
      '..ouuuuuuuuuuo..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 3 — Star Fox (orange, white muzzle)
  {
    palette: { o, w, c, r: '#e8833a', m: '#f6ead8', n: '#5a3b28' },
    rows: [
      '.oo.........oo..',
      '.oro........oro.',
      '.orro......orro.',
      '.orrroooooorrro.',
      '.orrrrrrrrrrrro.',
      'orrrrrrrrrrrrrro',
      'orrrworrrrworrro',
      'orrroorrrroorrro',
      'orrmmmmnnmmmmrro',
      'ocrmmmmnnmmmmrco',
      'orrmmmmmmmmmmrro',
      '.orrmmmmmmmmrro.',
      '.orrrmmmmmmrrro.',
      '..orrrrrrrrrro..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 4 — Cosmo Panda (white face, black patches)
  {
    palette: { o, w, c, k: '#2b2b38', u: '#f4f4fa', n: '#3a3a48' },
    rows: [
      '................',
      '..ooo......ooo..',
      '.okkko....okkko.',
      '.okkkkoooookkko.',
      '.okkuuuuuuuukko.',
      'okuuuuuuuuuuuuko',
      'okukkwuuuuwkkuko',
      'okukkkuuuukkkuko',
      'okuuuuunnuuuuuko',
      'ocuuuuunnuuuuuco',
      'okuuuuuoouuuuuko',
      'okuuuuuuuuuuuuko',
      '.okkuuuuuuuukko.',
      '..okkkkkkkkkko..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 5 — Nebula Hamster (golden, chubby cream cheeks)
  {
    palette: { o, w, c, h: '#eec06a', m: '#f9ecd2', n: '#5a3b28' },
    rows: [
      '................',
      '..oo........oo..',
      '.ohho......ohho.',
      '.ohhhoooooohhho.',
      '.ohhhhhhhhhhhho.',
      'ohhhhhhhhhhhhhho',
      'ohhhwohhhhwohhho',
      'ohhhoohhhhoohhho',
      'ohhmmmmnnmmmmhho',
      'ochmmmmnnmmmmhco',
      'ohhhmmmmmmmmhhho',
      'ohhhhhhhhhhhhhho',
      '.ohhhhhhhhhhhho.',
      '..ohhhhhhhhhho..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 6 — Polar Penguin (black hood, white face, orange beak)
  {
    palette: { o, w, c, k: '#2e3247', u: '#f4f4fa', z: '#f2a33c' },
    rows: [
      '................',
      '....oooooooo....',
      '..ookkkkkkkkoo..',
      '.okkkkkkkkkkkko.',
      '.okkkkkkkkkkkko.',
      'okkuuuuuuuuuukko',
      'okuuwouuuuwouuko',
      'okuuoouuuuoouuko',
      'okuuuuzzzzuuuuko',
      'okcuuzzzzzzuucko',
      'okuuuuzzzzuuuuko',
      'okkuuuuuuuuuukko',
      '.okkkuuuuuukkko.',
      '..okkkkkkkkkko..',
      '...oooooooooo...',
      '................',
    ],
  },
  // 7 — Little Alien (green, antennae with star tips, big eyes)
  {
    palette: { o, w, c, a: '#7fd66f', k: '#1c1c2c', s: '#ffe9a0' },
    rows: [
      '...s........s...',
      '...o........o...',
      '...o........o...',
      '..oaaooooooaao..',
      '.oaaaaaaaaaaaao.',
      'oaaaaaaaaaaaaaao',
      'oakkkwaaaawkkkao',
      'oakkkkaaaakkkkao',
      'oakkkkaaaakkkkao',
      'ocaaaaaaaaaaaaco',
      'oaaaaaooooaaaaao',
      'oaaaaaaaaaaaaaao',
      '.oaaaaaaaaaaaao.',
      '..oaaaaaaaaaao..',
      '...oooooooooo...',
      '................',
    ],
  },
];
