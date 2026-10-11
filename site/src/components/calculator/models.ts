import { type ModelId, MODELS } from '../../utils/pricing'

/** Every model the picker offers; invite-only models are not selectable. */
export const PICKABLE_MODELS: readonly ModelId[] = (Object.keys(MODELS) as ModelId[]).filter(
  (id) => !MODELS[id].inviteOnly,
)
