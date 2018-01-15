# Copyright 2018 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .result import SKIPPED


"""
Pipeline

Test processors are chained together and communicate with each other by
calling previous/next processor in the chain.
     ----next_test()---->     ----next_test()---->
Proc1                    Proc2                    Proc3
     <---result_for()----     <---result_for()----

For every next_test there is exactly one result_for call.
If processor ignores the test it has to return SkippedResult.
If it created multiple subtests for one test and wants to pass all of them to
the previous processor it can enclose them in GroupedResult.


Subtests

When test processor needs to modify the test or create some variants of the
test it creates subtests and sends them to the next processor.
Each subtest has:
- procid - globally unique id that should contain id of the parent test and
          some suffix given by test processor, e.g. its name + subtest type.
- processor - which created it
- origin - pointer to the parent (sub)test
"""


class TestProc(object):
  def __init__(self):
    self._prev_proc = None
    self._next_proc = None

  def connect_to(self, next_proc):
    """Puts `next_proc` after itself in the chain."""
    next_proc._prev_proc = self
    self._next_proc = next_proc

  def next_test(self, test):
    """
    Method called by previous processor whenever it produces new test.
    This method shouldn't be called by anyone except previous processor.
    """
    raise NotImplementedError()

  def result_for(self, test, result):
    """
    Method called by next processor whenever it has result for some test.
    This method shouldn't be called by anyone except next processor.
    """
    raise NotImplementedError()

  def heartbeat(self):
    if self._prev_proc:
      self._prev_proc.heartbeat()

  ### Communication

  def _send_test(self, test):
    """Helper method for sending test to the next processor."""
    self._next_proc.next_test(test)

  def _send_result(self, test, result):
    """Helper method for sending result to the previous processor."""
    self._prev_proc.result_for(test, result)



class TestProcObserver(TestProc):
  """Processor used for observing the data."""

  def next_test(self, test):
    self._on_next_test(test)
    self._send_test(test)

  def result_for(self, test, result):
    self._on_result_for(test, result)
    self._send_result(test, result)

  def heartbeat(self):
    self._on_heartbeat()
    super(TestProcObserver, self).heartbeat()

  def _on_next_test(self, test):
    """Method called after receiving test from previous processor but before
    sending it to the next one."""
    pass

  def _on_result_for(self, test, result):
    """Method called after receiving result from next processor but before
    sending it to the previous one."""
    pass

  def _on_heartbeat(self):
    pass


class TestProcProducer(TestProc):
  """Processor for creating subtests."""

  def __init__(self, name):
    super(TestProcProducer, self).__init__()
    self._name = name

  def next_test(self, test):
    self._next_test(test)

  def result_for(self, subtest, result):
    self._result_for(subtest.origin, subtest, result)

  ### Implementation
  def _next_test(self, test):
    raise NotImplementedError()

  def _result_for(self, test, subtest, result):
    """
    result_for method extended with `subtest` parameter.

    Args
      test: test used by current processor to create the subtest.
      subtest: test for which the `result` is.
      result: subtest execution result created by the output processor.
    """
    raise NotImplementedError()

  ### Managing subtests
  def _create_subtest(self, test, subtest_id, **kwargs):
    """Creates subtest with subtest id <processor name>-`subtest_id`."""
    return test.create_subtest(self, '%s-%s' % (self._name, subtest_id),
                               **kwargs)


class TestProcFilter(TestProc):
  """Processor for filtering tests."""

  def next_test(self, test):
    if self._filter(test):
      self._send_result(test, SKIPPED)
    else:
      self._send_test(test)

  def result_for(self, test, result):
    self._send_result(test, result)

  def _filter(self, test):
    """Returns whether test should be filtered out."""
    raise NotImplementedError()
