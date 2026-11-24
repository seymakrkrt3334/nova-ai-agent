require 'json'

package = JSON.parse(File.read(File.join(__dir__, '..', 'package.json')))

Pod::Spec.new do |s|
  s.name           = 'NovaAssistant'
  s.version        = package['version']
  s.summary        = 'NOVA phone assistant'
  s.homepage       = 'https://localhost'
  s.license        = 'MIT'
  s.author         = 'NOVA'
  s.platforms      = { :ios => '15.1' }
  s.source         = { :git => '' }
  s.source_files   = '**/*.{h,m,swift}'
  s.dependency 'ExpoModulesCore'
end
