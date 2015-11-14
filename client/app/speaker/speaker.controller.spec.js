'use strict';

describe('Controller: SpeakerCtrl', function () {

  // load the controller's module
  beforeEach(module('scotusChatApp'));

  var SpeakerCtrl, scope;

  // Initialize the controller and a mock scope
  beforeEach(inject(function ($controller, $rootScope) {
    scope = $rootScope.$new();
    SpeakerCtrl = $controller('SpeakerCtrl', {
      $scope: scope
    });
  }));

  it('should ...', function () {
    expect(1).toEqual(1);
  });
});
