# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format. 

## [0.1.0] -- 2021-6-17

- Simplified schema definitions to remove the `recursive` keyword; now anything with `henge_class` is assumed to be recursive. All `object` and `array` types must define `henge_class`.
- Added capability to recurse on arrays, and on primitive types (like `string`). You no longer need wrap primitive types in objects to enable recursion.
- Introduced 'flexible digests' concept, which 
- Separated the schemas parameters in the constructor so there are different args for file paths or strings.

## [0.0.3] -- 2020-06-27

- Added capability for automatically dividing hierarchical schemas in henge construction
- Added some support for array object types

## [0.0.2] -- 2020-01-23

### Added 

* Initial project release

